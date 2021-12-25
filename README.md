# fav-player

This is the MP3 Player

Configuration
=============

The following parameters need to be defined
```
  DATABASE_HOST: the IP of the database
  DATABASE_NAME: database name
  DATABASE_PORT: port to connect to the database 
  DATABASE_USER: username of the database
  ACCESS_TOKEN: access token to connect to the database admin
  APP_PORT: port to connect to the APP
```

Deployment
==========

For deployment of both the music database service and the web service you will need to have a kubernetes cluster
There are several ways for that, this link provides an example on how to use it with the Docker desktop app
https://medium.com/backbase/kubernetes-in-local-the-easy-way-f8ef2b98be68

Once you have that you can install the kubernetes dashboard with this

```kubectl apply -f https://raw.githubusercontent.com/kubernetes/dashboard/v2.0.0-rc3/aio/deploy/recommended.yaml```

To access to the overview you need to start a kubectl proxy
 
 ```kubectl proxy```
 
 and then you can go to
[Local kubernetes overview](http://localhost:8001/api/v1/namespaces/kubernetes-dashboard/services/https:kubernetes-dashboard:/proxy/#/overview)

In order to access you need to get an auth token, you can do it with this oneliner
```kubectl -n kube-system describe secret $(kubectl -n kube-system get secret | awk '/^deployment-controller-token-/{print $1}') | awk '$1=="token:"{print $2}'```

To create the database secret in kubernetes you have to add it like this:

```apiVersion: v1
kind: Secret
metadata:
  name: dbrootpassword
type: kubernetes.io/basic-auth
stringData:
  username: admin
  mysql-root-password: t0p-Secret
```
  
 You will also need a config map with values like this
 
```apiVersion: v1
kind: ConfigMap
metadata:
  name: musicdb-config
data:
  DATABASE_HOST: "musicdb"
  DATABASE_NAME: "music_test"
  DATABASE_PORT: "330"
  DATABASE_USER: "admin"
  ACCESS_TOKEN: "666"
  APP_PORT: 2020
```