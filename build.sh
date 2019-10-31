set -v   
pip install django
pip install python-miio
git clone git@gitlab.act.buaa.edu.cn:yebw/pyxiaomigateway.git
cd PyXiaomiGateway
pip install wheel
python setup.py bdist_wheel
pip install dist/PyXiaomiGateway-0.12.4-py3-none-any.whl
