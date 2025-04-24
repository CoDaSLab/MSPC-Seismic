docker stop digivolcan_dev
docker rm digivolcan_dev
docker run -it -d -v /daaas/ldauria:/home/vulcano  --name digivolcan_dev digivolcan_dev
