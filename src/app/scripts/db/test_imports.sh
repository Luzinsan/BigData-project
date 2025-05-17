#!/bin/bash

export HADOOP_ROOT_LOGGER=WARN,console
ENV_FILE=$(find $(pwd) -maxdepth 4 -name ".env" | head -1)

get_env_var() {
  grep -o "$1='[^']*'" "$ENV_FILE" | sed "s/$1='\(.*\)'/\1/"
}

DB_NAME=$(get_env_var "DB_NAME")
DB_USER=$(get_env_var "DB_USER")
DB_PASSWORD=$(get_env_var "DB_PASSWORD")
DB_HOST=$(get_env_var "DB_HOST")
DB_PORT=$(get_env_var "DB_PORT")

echo "DB_HOST: $DB_HOST"
echo "DB_PORT: $DB_PORT"
echo "DB_NAME: $DB_NAME"

BASE_DIR="/project/warehouse/benchmark_tests"
hdfs dfs -rm -r -skipTrash $BASE_DIR
hdfs dfs -mkdir -p $BASE_DIR

declare -a FORMATS=("avro" "parquet")
declare -a CODECS=("Gzip" "Snappy" "Bzip2")

echo "Retrieving all tables from database..."
TABLES=$(PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -t -c "
  SELECT table_name FROM information_schema.tables 
  WHERE table_schema='public' AND table_type='BASE TABLE';
")

declare -a TABLE_ARRAY=()
while IFS= read -r line; do
  line=$(echo "$line" | xargs)
  if [ ! -z "$line" ]; then
    TABLE_ARRAY+=("$line")
  fi
done <<< "$TABLES"

echo "Found ${#TABLE_ARRAY[@]} tables: ${TABLE_ARRAY[*]}"

test_format_compression() {
  local table=$1
  local format=$2
  local codec=$3
  local codec_class
  local avro_codec
  
  case $codec in
    "Gzip") 
      codec_class="org.apache.hadoop.io.compress.GzipCodec" 
      avro_codec="deflate"
      ;;
    "Snappy") 
      codec_class="org.apache.hadoop.io.compress.SnappyCodec" 
      avro_codec="snappy"
      ;;
    "Bzip2") 
      codec_class="org.apache.hadoop.io.compress.BZip2Codec" 
      avro_codec="bzip2"
      ;;
  esac
  
  local target_dir="$BASE_DIR/${table}_${format}_${codec}"
  
  echo "===================================================="
  echo "Testing: $table with $format and $codec"
  echo "===================================================="
  
  echo "Import start: $(date)"
  import_start=$(date +%s)
  
  if [ "$format" == "avro" ]; then
    format_option="--as-avrodatafile"
    codec_option="--compression-codec $avro_codec"
  else
    format_option="--as-parquetfile"
    codec_option="--compression-codec $codec_class"
  fi
  
  sqoop import \
    --connect "jdbc:postgresql://$DB_HOST:$DB_PORT/$DB_NAME" \
    --username "$DB_USER" \
    --password "$DB_PASSWORD" \
    --table "$table" \
    --target-dir "$target_dir" \
    $format_option \
    $codec_option \
    --null-string '\\N' \
    --null-non-string '\\N' \
    --m 1 \
    2> /dev/null
  
  sqoop_exit=$?
  
  import_end=$(date +%s)
  import_time=$((import_end - import_start))
  echo "Import time: $import_time seconds"
  
  if [ $sqoop_exit -ne 0 ]; then
    echo "Sqoop import failed for $table with $format and $codec"
    echo "$table,$format,$codec,FAILED,$import_time,NA,NA,NA" >> benchmark_results.csv
    return
  fi
  
  if hdfs dfs -test -d "$target_dir"; then
    size_bytes=$(hdfs dfs -du -s "$target_dir" | awk '{print $1}')
    if [ -z "$size_bytes" ]; then
      size_bytes=0
    fi
    size_mb=$(awk "BEGIN {printf \"%.2f\", $size_bytes/1024/1024}")
    echo "Size in HDFS: $size_mb MB"
  else
    echo "Directory $target_dir does not exist"
    size_bytes=0
    size_mb=0
  fi
  
  original_size=$(PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -t -c "
    SELECT pg_total_relation_size('$table');
  ")
  if [ -z "$original_size" ]; then
    original_size=1
  fi
  original_size_mb=$(awk "BEGIN {printf \"%.2f\", $original_size/1024/1024}")
  
  if [ "$size_bytes" -ne 0 ]; then
    compression_ratio=$(awk "BEGIN {printf \"%.2f\", $original_size/$size_bytes}")
  else
    compression_ratio=0
  fi
  echo "Compression ratio: $compression_ratio"
  
  echo "Read test start: $(date)"
  read_start=$(date +%s)
  
  if [ "$format" == "avro" ]; then
    timeout 60s spark-sql --packages org.apache.spark:spark-avro_2.12:3.5.4 \
      -e "SELECT COUNT(*) FROM avro.\`$target_dir\`"
  else
    timeout 60s spark-sql \
      -e "SELECT COUNT(*) FROM parquet.\`$target_dir\`"
  fi
  
  read_end=$(date +%s)
  read_time=$((read_end - read_start))
  echo "Read time: $read_time seconds"
  
  echo "$table,$format,$codec,$size_mb,$original_size_mb,$compression_ratio,$import_time,$read_time" >> benchmark_results.csv
}

echo "Table,Format,Codec,Size_MB,Original_Size_MB,Compression_Ratio,Import_Time_sec,Read_Time_sec" > benchmark_results.csv

if [ ${#TABLE_ARRAY[@]} -eq 0 ]; then
  echo "No tables found. Please check database connection."
  exit 1
fi

for table in "${TABLE_ARRAY[@]}"; do
  echo "Processing table: $table"
  for format in "${FORMATS[@]}"; do
    for codec in "${CODECS[@]}"; do
      test_format_compression "$table" "$format" "$codec"
    done
  done
done

echo
echo "==========================================================================="
echo "                         BENCHMARK RESULTS SUMMARY                         "
echo "==========================================================================="

if [ ! -s benchmark_results.csv ] || [ $(wc -l < benchmark_results.csv) -le 1 ]; then
  echo "No benchmark results were recorded. Check for errors in the log."
  exit 1
fi

echo "Table-wise Best Results:"
for table in "${TABLE_ARRAY[@]}"; do
  if grep -q "^$table," benchmark_results.csv; then
    echo
    echo "Table: $table"
    printf "| %-10s | %-10s | %-12s | %-14s | %-15s | %-15s |\n" "Format" "Codec" "Size (MB)" "Comp. Ratio" "Import Time (s)" "Read Time (s)"
    echo "|-----------+------------+--------------+----------------+-----------------+-----------------|"
    
    best_comp=$(grep "^$table," benchmark_results.csv | grep -v "FAILED" | sort -t, -k6 -nr | head -1)
    if [ -n "$best_comp" ]; then
      best_comp_format=$(echo $best_comp | cut -d, -f2)
      best_comp_codec=$(echo $best_comp | cut -d, -f3)
      best_comp_size=$(echo $best_comp | cut -d, -f4)
      best_comp_ratio=$(echo $best_comp | cut -d, -f6)
      best_comp_import=$(echo $best_comp | cut -d, -f7)
      best_comp_read=$(echo $best_comp | cut -d, -f8)
      
      printf "| %-10s | %-10s | %-12s | %-14s | %-15s | %-15s |\n" \
        "$best_comp_format" "$best_comp_codec" "$best_comp_size" "$best_comp_ratio" "$best_comp_import" "$best_comp_read"
    fi
      
    best_read=$(grep "^$table," benchmark_results.csv | grep -v "FAILED" | sort -t, -k8 -n | head -1)
    if [ -n "$best_read" ] && [ "$best_comp" != "$best_read" ]; then
      best_read_format=$(echo $best_read | cut -d, -f2)
      best_read_codec=$(echo $best_read | cut -d, -f3)
      best_read_size=$(echo $best_read | cut -d, -f4)
      best_read_ratio=$(echo $best_read | cut -d, -f6)
      best_read_import=$(echo $best_read | cut -d, -f7)
      best_read_read=$(echo $best_read | cut -d, -f8)
      
      printf "| %-10s | %-10s | %-12s | %-14s | %-15s | %-15s |\n" \
        "$best_read_format" "$best_read_codec" "$best_read_size" "$best_read_ratio" "$best_read_import" "$best_read_read"
    fi
  fi
done

echo "==========================================================================="
echo "Overall Best Formats and Codecs:"
echo

if grep -v "FAILED" benchmark_results.csv | grep -q -v "^Table,"; then
  overall_best_comp=$(grep -v "FAILED" benchmark_results.csv | grep -v "^Table," | sort -t, -k6 -nr | head -1)
  overall_best_comp_table=$(echo $overall_best_comp | cut -d, -f1)
  overall_best_comp_format=$(echo $overall_best_comp | cut -d, -f2)
  overall_best_comp_codec=$(echo $overall_best_comp | cut -d, -f3)
  overall_best_comp_ratio=$(echo $overall_best_comp | cut -d, -f6)

  overall_best_read=$(grep -v "FAILED" benchmark_results.csv | grep -v "^Table," | sort -t, -k8 -n | head -1)
  overall_best_read_table=$(echo $overall_best_read | cut -d, -f1)
  overall_best_read_format=$(echo $overall_best_read | cut -d, -f2)
  overall_best_read_codec=$(echo $overall_best_read | cut -d, -f3)
  overall_best_read_time=$(echo $overall_best_read | cut -d, -f8)

  echo "* Best compression: $overall_best_comp_format with $overall_best_comp_codec (ratio: $overall_best_comp_ratio on table $overall_best_comp_table)"
  echo "* Fastest read: $overall_best_read_format with $overall_best_read_codec (time: $overall_best_read_time sec on table $overall_best_read_table)"
else
  echo "No valid benchmark results found."
fi

echo
echo "Benchmark completed: $(date)"
echo "Detailed results are available in benchmark_results.csv"