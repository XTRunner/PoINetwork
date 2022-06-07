# PoINetwork

Road network embedded with Points of interest, implemented in Python 3.7

More details can be found in our paper, https://ieeexplore.ieee.org/document/9162294

*X. Teng, G. Trajcevski, J. -S. Kim and A. Züfle, "Semantically Diverse Path Search," 2020 21st IEEE International Conference on Mobile Data Management (MDM), 2020, pp. 69-78, doi: 10.1109/MDM48529.2020.00028.*

- `tripAdvisorCrawler/tripAdvisorCrawler/spiders`: Web HTML crawler for collecting reviews information of attratctions from TripAdvisor (https://www.tripadvisor.com)

- `geocode.py`: Retrieve the longtitude and latitude based on physical address

- `graph_construct.py`: Construct PoI road network from two different resources - Regular road network and PoI dataset

Example PoI network: `PoI_Network/NY_es.csv` and `PoI_Network/NY_ns.csv` for edge and node information, respectively

Please feel free to contact xuteng@iastate.edu if you are interested in this work. 



