# stock_personalised_alerts
this project will give personalised intimation on list of stocks that you want 


pip install nsepython
pip install pandas

Market capitalization = total number of outstanding shares multiplied by the market price of each share.

largestocks => market cap of these companies is significantly high, coming in at around Rs. 20,000 crores or more.

midstocks => market cap generally tends to range from Rs. 5,000 to Rs. 20,000 crores.

smallstocks => companies generally come in below Rs. 5,000 crores

.env file create add variables there and run app.py


docker build -t stock-analyzer .
docker tag stock-analyzer truenas_ip:30095/stock-analyzer
docker push truenas_ip:30095/stock-analyzer

docker pull truenas_ip:30095/stock-analyzer

to update with latest code
docker build -t stock-analyzer .
docker rmi truenas_ip:30095/stock-analyzer
docker tag stock-analyzer truenas_ip:30095/stock-analyzer
docker push truenas_ip:30095/stock-analyzer
