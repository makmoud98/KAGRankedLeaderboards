# KAG Ranked Leaderboards
This project was created for the fourth project in my Full Stack Web Developer Nanodegree Program.  
This is written in python and uses flask and sqlalchemy with sqlite for the database.  
This shows my ability to use the flask framework to add CRUD functionality to a website.  
The python code was verified with PEP8 to ensure readability.  
Program was tested using python v2.7.12, sqlalchemy v2.3.2, flask v0.12.2, requests v2.18.4, enum34 v1.1.6, oauth2client v4.1.2, and imageio v2.2.0
  
# Running it on Ubuntu 16.04
- *install the required dependencies*  
`apt-get install python`  
`apt-get install sqlite3`  
`apt-get install python python-pip`  
`pip2 install --upgrade pip`  
`pip2 install flask`  
`pip2 install sqlalchemy`  
`pip2 install oauth2client`  
`pip2 install requests`  
`pip2 install enum34`  
`pip2 install imageio`  
- *setup the database*  
`python setup_database.py`  
- *setup your google oauth client id*  
navigate to https://console.developers.google.com/  
create a new project  
navigate to https://console.developers.google.com/apis/credentials  
create a new "OAuth client ID"  
download the json  
rename the file to `client_secrets.json`  
place the file in the root of the project  
- *change secret key*  
open project.py with a text editor  
navigate to the bottom of the page
`app.secret_key = 'change me'`  
be sure the change the string to something else  
- *start the web server*  
`python project.py`  
- *give yourself admin permissions*  
log into the website with your google account  
shutdown the web server  
`python new_admin.py`  
follow on-screen prompts  
restart the web server  
  
  
