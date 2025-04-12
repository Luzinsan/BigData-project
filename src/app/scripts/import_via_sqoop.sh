username=$(sed -n 2p .env | cut -d= -f2 | tr -d "'\"")
password=$(sed -n 3p .env | cut -d= -f2 | tr -d "'\"")

# import all tables from database
sqoop import-all-tables \ 
--connect jdbc:postgresql://hadoop-04.uni.innopolis.ru/team3_projectdb \
--username $username \
--password $password \
--compression-codec=snappy \
--compress --as-parquetfile \
--warehouse-dir=project/warehouse --m 1

# get all tables from database  
# sqoop list-tables \
# --connect jdbc:postgresql://hadoop-04.uni.innopolis.ru/team3_projectdb \
# --username $username \
# --password $password

# import specific tables
# sqoop import \
# --connect jdbc:postgresql://hadoop-04.uni.innopolis.ru/team3_projectdb \
# --username team3 \
# --password $password \
# --compression-codec=snappy --compress \
# --as-parquetfile \
# --warehouse-dir=project/warehouse --m 1 \
# --table locations \
# --columns h3_09, lat, lon