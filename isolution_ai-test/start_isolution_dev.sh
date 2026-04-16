kill -9 `lsof -t -i:9001`
nohup python isolution_run.py --env dev > nohup.out &