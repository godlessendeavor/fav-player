# Use an official Python runtime as a parent image
FROM python:3.6

RUN mkdir /MusicDatabaseServer
# Set the working directory to /MusicDatabaseServer
WORKDIR /MusicDatabaseServer

# Copy the current directory contents into the container at /app
COPY . /MusicDatabaseServer

# Install any needed packages specified in requirements.txt
RUN pip install --trusted-host pypi.python.org -r requirements.txt

# Make port 2020 available to the world outside this container
EXPOSE 2020


# Run app.py when the container launches
CMD ["python", "app.py"]
