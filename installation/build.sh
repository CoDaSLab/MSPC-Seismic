docker  stop digivolcan_dev
docker  rm digivolcan_dev
docker image rm digivolcan_dev:latest
docker build -t digivolcan_dev:latest .
