# Multi Agent-Based-Simulation for Dengue Spread

### This research contributes to vector control by introducing a MABS to simulate the spread of Dengue disease in urban areas.
1. Study Contribution

> This research contributes to vector control by introducing a MABS to simulate the spread of Dengue disease in urban areas. 
> Our study analyzes seven years of reported Dengue cases in two Brazilian cities, Alto Santo and Limoeiro.
> We employ a methodological approach to define street blocks using GIS data from OSM and integrate historical case notifications into these defined blocks.
> The results indicate that the proposed simulation is a valuable tool with the potential to enhance vector control strategies and improve public health outcomes.
> By generating visualizations of multiple future case scenarios based on real historical notifications, our approach supports more informed decision-making.
> These findings have important implications for public health authorities, policymakers, and researchers tackling the complex challenges of vector-borne diseases.
> Furthermore, MABS can assist health departments in defining more effective interventions and optimizing resource allocation for vector control efforts.

2. Basic Simulation Description 

> The model has four types of agents that could have some interactions with each other: ***mosquito, human, egg, and breeding site***.
> The size of the human and breeding site populations does not change during the simulation. 
> The mosquito agent is divided into two phases: aquatic and adult. 
> The breeding site agent represents a point on the map that allows mosquitoes to lay eggs to proliferate new individuals for the population, independent of the current state.
> The mosquitoes in the starting population and those generated during the simulation are associated with a breeding site.

3. Results and Analysis

> See the paper: [Multi-agent simulation for dengue spread forecast: A case study for two Brazilian cities](https://www.sciencedirect.com/science/article/abs/pii/S0304380025004144) to see a complete analysis of this simulation.

4. How to cite
```bash
@article{ARAUJO2026111428,
title = {Multi-agent simulation for dengue spread forecast: A case study for two Brazilian cities},
journal = {Ecological Modelling},
volume = {513},
pages = {111428},
year = {2026},
issn = {0304-3800},
doi = {https://doi.org/10.1016/j.ecolmodel.2025.111428},
url = {https://www.sciencedirect.com/science/article/pii/S0304380025004144},
author = {Carlos Victor Dantas Araújo and Fábio Luiz Usberti and Emily Brito {de Oliveira} and Laura Silva {de Assis} and Celso Cavellucci}}
```
