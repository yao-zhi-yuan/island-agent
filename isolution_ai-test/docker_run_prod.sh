docker build -t isolution_ai .
docker run -d -p 9002:9002 isolution_ai python -u isolution_run.py --env prod