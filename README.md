# Hackathon2020


Start dashboard in terminal:

    python3 dashboard.py


Start node:

    curl http://127.0.0.1:8000/new_node (or in browser)

or manually in terminal:

    python3 node.py --host=127.0.0.1 --port=8001 --control_host=127.0.0.1 --control_port=8000

Visualize in browser:

    http://127.0.0.1:8000/static/index.html


Windows WSL Ubuntu 18.04 LTS (Python 3.6+ required)

    sudo apt install mysql-server python3 python3-pip
    sudo pip3 install -U setuptools pip
    sudo pip3 install -r requirements.txt

## Tools

https://www.heidisql.com/download.php?download=portable-64

## Update MySQL PWD

    sudo -s
    mysql -uroot

    use mysql
    update user set authentication_string=PASSWORD('root') where User='root';
    update user set plugin="mysql_native_password" where User='root';
    flush privileges;
    quit;

