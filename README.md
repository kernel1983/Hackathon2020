# Hackathon2020


Start dashboard in Terminal (WSL Ubuntu 18.04 LTS):

    python3 dashboard.py


Start node one by one through dashboard API:

    curl http://127.0.0.1:8000/new_node (or in browser)

or manually in terminal (try byobu):

    python3 node.py --host=127.0.0.1 --port=8001 --control_host=127.0.0.1 --control_port=8000

Visualize in browser:

    http://127.0.0.1:8000/static/index.html


## Tips

Windows WSL Ubuntu 18.04 LTS (Python 3.6+ required) (The packages version in requirements.txt are important)

    sudo apt install mysql-server python3 python3-pip
    sudo pip3 install -U setuptools pip
    sudo pip3 install -r requirements.txt

Update MySQL PWD and create database

    sudo -s
    service mysql start
    mysql -uroot

    create database nodes;

    use mysql
    update user set authentication_string=PASSWORD('root') where User='root';
    update user set plugin="mysql_native_password" where User='root';
    flush privileges;
    quit;

HeidiSQL

https://www.heidisql.com/download.php?download=portable-64
