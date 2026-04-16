kill -9 `lsof -t -i:9002`
nohup python isolution_run.py --env prod > nohup.out &