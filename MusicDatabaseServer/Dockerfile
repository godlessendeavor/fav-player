# Use an official Python runtime as a parent image
FROM python:3.8-slim-buster

WORKDIR /
RUN useradd -ms /bin/bash musicdb
RUN chown musicdb /

# Copy the current directory contents into the container at /
COPY . /

# Install any needed packages specified in requirements.txt
RUN pip install --trusted-host pypi.python.org -r requirements.txt

# Make port 2020 available to the world outside this container
EXPOSE 2020

USER musicdb
# Run app.py when the container launches
CMD ["python", "app.py"]
