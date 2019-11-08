set -v   
pip install django
pip install sshtunnel
pip install pymysql
pip install python-miio
git clone https://github.com/barrierye/PyXiaomiGateway.git
cd PyXiaomiGateway
pip install wheel
python setup.py bdist_wheel
pip install dist/PyXiaomiGateway-0.12.4-py3-none-any.whl
