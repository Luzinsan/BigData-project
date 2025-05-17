===========================================================================
                         BENCHMARK RESULTS SUMMARY                         
===========================================================================
Table-wise Best Results:

Table: locations
| Format     | Codec      | Size (MB)    | Comp. Ratio    | Import Time (s) | Read Time (s)   |
|-----------+------------+--------------+----------------+-----------------+------------------|
| avro       | Bzip2      | 0.06         | 11.97          | 16              | 13              |
| avro       | Snappy     | 0.10         | 6.87           | 15              | 12              |
| parquet    | Gzip       | 0.06         | 10.87          | 16              | 12              |

Table: transactions
| Format     | Codec      | Size (MB)    | Comp. Ratio    | Import Time (s) | Read Time (s)   |
|-----------+------------+--------------+----------------+-----------------+------------------|
| parquet    | Gzip       | 71.09        | 9.14           | 51              | 13              |
| parquet    | Snappy     | 94.13        | 6.90           | 40              | 12              |


Table: cash_withdrawals

| Format     | Codec      | Size (MB)    | Comp. Ratio    | Import Time (s) | Read Time (s)   |
|-----------+------------+--------------+----------------+-----------------+------------------|
| avro       | Bzip2      | 0.64         | 25.04          | 17              | 13              |
| parquet    | Gzip       | 0.66         | 24.43          | 16              | 12              |


Table: moscow

| Format     | Codec      | Size (MB)    | Comp. Ratio    | Import Time (s) | Read Time (s)   |
|-----------+------------+--------------+----------------+-----------------+------------------|
| parquet    | Gzip       | 14.08        | 9.24           | 20              | 12              |
| parquet    | Snappy     | 23.81        | 5.46           | 19              | 13              |

===========================================================================
Overall Best Formats and Codecs:

* Best compression: avro with Bzip2 (ratio: 25.04 on table cash_withdrawals)
* Fastest read: parquet with Gzip (time: 12 sec on table cash_withdrawals)

Benchmark completed: Sat May 17 18:10:42 MSK 2025
Detailed results are available in benchmark_results.csv