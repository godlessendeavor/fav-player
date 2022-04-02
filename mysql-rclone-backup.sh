#!/bin/bash
##this script will backup mysql and upload it to google drive 
##mysql container id
CONTAINER=$1
##directory name
DIRNAME=$2;
##database name
DATABASEe=$3;
##database username
DBUSER=$4;
##database password
DBPASS=$5;
## rclone remote name
RCLONE_REMOTE_NAME=$6;
##google drive folder name
GDRIVE_FOLDER_NAME=$7;
##condition to check folder exist or not 
if [ ! -d "$DIRNAME" ]
then
    ##create directory
    mkdir ./$DIRNAME
    ##dump mysql database on server
    docker exec $CONTAINER /usr/bin/mysqldump -u $DBUSER -p$DBPASS $DATABASEe | gzip>"./$DIRNAME/$DATABASEe($(date +\%Y_\%m_\%d_\%H)).sql.gz"
    ##wait for 10 seconds
    sleep 10
    ##upload it to google drive
    rclone copy "./$DIRNAME/$DATABASEe($(date +\%Y_\%m_\%d_\%H)).sql.gz" $RCLONE_REMOTE_NAME:$GDRIVE_FOLDER_NAME
##if folder already exist
else
    ##dump mysql database on server
    mysqldump -u $DBUSER -p$DBPASS $DATABASEe | gzip>"./$DIRNAME/$DATABASEe($(date +\%Y-\%m-\%d-\%H)).sql.gz"
     ##wait for 10 seconds
    sleep 10
    ##upload it to google drive
    rclone copy "./$DIRNAME/$DATABASEe($(date +\%Y-\%m-\%d-\%H)).sql.gz" $RCLONE_REMOTE_NAME:$GDRIVE_FOLDER_NAME
    ##delete 10 days older file on server to save disk space
    find ./$DIRNAME -mtime +10 -type f -delete
fi
exit 0;
