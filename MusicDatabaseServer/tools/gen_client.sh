cd ~/workspace/tools
java -jar swagger-codegen-cli.jar generate -i http://0.0.0.0:2020/swagger.json -l python -o /tmp/python_api_client -c /home/thrasher/jba/fav-player/MusicDatabaseServer/tools/swagger_client_gen_config.json 
cd /tmp/python_api_client
sudo python3 setup.py install
