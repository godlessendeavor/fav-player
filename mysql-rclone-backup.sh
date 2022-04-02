#!/bin/bash
##this script will backup mysql and upload it to google drive 
##mysql container id
CONTAINER=$1
## directory path
DIRPATH=$2
##directory name
DIRNAME=$3;
##database name
DATABASE=$4;
##database username
DBUSER=$5;
##database password
DBPASS=$6;
## rclone remote name
RCLONE_REMOTE_NAME=$7;
##google drive folder name
GDRIVE_FOLDER_NAME=$8;
##condition to check folder exist or not 
if [ ! -d "$DIRPATH$DIRNAME" ]
then
    ##create directory
    mkdir $DIRPATH$DIRNAME
    ##dump mysql database on server
    docker exec $CONTAINER /usr/bin/mysqldump -u $DBUSER -p$DBPASS $DATABASEe | gzip>"$DIRPATH$DIRNAME/$DATABASE($(date +\%Y-\%m-\%d-\%H)).sql.gz"
    ##wait for 10 seconds
    sleep 10
    ##upload it to google drive
    rclone --config=/home/ubuntu/.config/rclone/rclone.conf copy "$DIRPATH$DIRNAME/$DATABASE($(date +\%Y-\%m-\%d-\%H)).sql.gz" $RCLONE_REMOTE_NAME:$GDRIVE_FOLDER_NAME
##if folder already exist
else
    ##dump mysql database on server
    docker exec $CONTAINER /usr/bin/mysqldump -u $DBUSER -p$DBPASS $DATABASEe | gzip>"$DIRPATH$DIRNAME/$DATABASE($(date +\%Y-\%m-\%d-\%H)).sql.gz"
     ##wait for 10 seconds
    sleep 10
    ##upload it to google drive
    rclone --config=/home/ubuntu/.config/rclone/rclone.conf copy "$DIRPATH$DIRNAME/$DATABASE($(date +\%Y-\%m-\%d-\%H)).sql.gz" $RCLONE_REMOTE_NAME:$GDRIVE_FOLDER_NAME
    ##delete 10 days older file on server to save disk space
    find $DIRPATH$DIRNAME -mtime +10 -type f -delete
fi
exit 0;
