cd ~/workspace/tools/swagger-codegen
java -jar modules/swagger-codegen-cli/target/swagger-codegen-cli.jar generate -i http://0.0.0.0:2020/swagger.json -l python -o /tmp/python_api_client -c /home/thrasher/workspace/fav-player/MusicDatabaseServer/tools/swagger_client_gen_config.json 
cd /tmp/python_api_client
sudo python3 setup.py install
