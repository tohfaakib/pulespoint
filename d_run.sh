docker stop pulse_point
docker rm pulse_point
docker build -t pulse_point .
docker run -d -p 8119:8119 -p 9050:9050 --name pulse_point pulse_point
