docker build -t isolution_ai .
docker run -d -p 9001:9001 isolution_ai python -u isolution_run.py --env test