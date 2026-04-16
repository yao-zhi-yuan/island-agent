kill -9 `lsof -t -i:9003`
nohup python isolution_run.py --env prod > nohup.out &