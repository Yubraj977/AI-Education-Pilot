# Python version 3.10-slim
ARG PYTHON_VERSION=3.10
FROM python:${PYTHON_VERSION}-slim as python-base

# Set the working directory in the container
WORKDIR /AI-Education-Pilot

RUN apt-get update && \
    apt-get install -y --no-install-recommends build-essential \
    curl \
    apt-utils \
    gnupg2 &&\
    rm -rf /var/lib/apt/lists/* && \
    pip install --upgrade pip

RUN apt-get update
RUN curl https://packages.microsoft.com/keys/microsoft.asc | apt-key add -
RUN curl https://packages.microsoft.com/config/debian/11/prod.list > /etc/apt/sources.list.d/mssql-release.list 

RUN exit
RUN apt-get update
RUN env ACCEPT_EULA=Y apt-get install -y msodbcsql18 

COPY requirements.txt .

COPY /odbc.ini / 
RUN odbcinst -i -s -f /odbc.ini -l
RUN cat /etc/odbc.ini

RUN pip install -r requirements.txt
# Copy the current directory contents into the container
COPY . /AI-Education-Pilot

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Expose port (assuming Streamlit defaults to 8501)
EXPOSE 8501

# Define the command to run the app using Streamlit
CMD ["streamlit", "run", "app.py"]
