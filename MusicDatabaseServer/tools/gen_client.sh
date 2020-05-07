#/bin/bash
while getopts ":ht" opt; do
  case ${opt} in
    h ) # process option h
      echo "Use option u to upload the generated client to Pypi otherwise ti will install locally"
      ;;
    u ) # process option u
      upload=True
      ;;
    \? ) echo "Usage: cmd [-h] [-t]"
      ;;
  esac
done

# generate the client
#TODO: add version number as option?
java -jar swagger-codegen-cli.jar generate -i ../open_api/app_definition.yaml -l python -o /tmp/python_api_client -c client_gen_config.json
cd /tmp/python_api_client
if [[ $upload == "True" ]]
then
  sudo python3 setup.py sdist # create distribution
  python3 -m twine upload dist/*
else
  sudo chown thrasher dist
  python3 setup.py install --force # install and upgrade if existing # TODO: check if pipenv is used with an argument
  wheel convert musicdb_client-1.0.3-py3.6.egg # TODO: version number to variable
  cd -
  pipenv install /tmp/python_api_client/dist/musicdb_client-1.0.3-py36-none-any.whl
fi

