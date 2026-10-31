# Kathmandu–Lalitpur Noise Atlas

A 3D noise map of Kathmandu and Lalitpur. It models road traffic, aircraft at Tribhuvan International Airport, markets and shops, and nightlife on a 20 m grid, then draws the result over 307,000 OpenStreetMap buildings with Three.js.

```
raw/            OpenStreetMap Overpass extracts + Terrarium DEM tiles (inputs, ~200 MB)
model/build.py  noise model: sources, propagation, hourly profiles, exposure stats
model/flightpaths.py  VNKT procedures from CAAN AIP Nepal (RNP AR approaches, SIDs, missed approaches, VFR passes, heli-lanes)
web/            viewer (index.html) + flight simulator (sim.js)
web/data/       model output: grid/dem/buildings/roads packed as lossless PNG byte streams + meta.json
```

## Run

```bash
python3 model/build.py && python3 model/pack.py   # rebuild web/data from raw/ (~15 s)
cd web && python3 -m http.server 8765
# open http://localhost:8765/
```

Views you can link to: `#night`, `#lden`, `#lnight`, `#relief`, `#airport`, `#thamel`.

## Model in brief

- **Roads**: each OSM way is a line source. Daytime level 10 m from the kerb depends on road class (trunk 76, primary 75, secondary 72, residential 55.5 dB(A)). Divided carriageways are split; lanes and unpaved surfaces add energy.
- **Aircraft**: tracks follow the CAAN AIP Nepal VNKT AD 2 coding tables (raw/aip): RNP Z/Y RWY 02, RNP RWY 20, VOR/DME RWY 02, SIDs DARKE 1F/1G/1H and IGRIS 1C/1D/1E, published missed approaches, domestic VFR via the valley passes and the heli-lanes. Separate noise layers for runway 02 and runway 20. ~400 movements a day follow CAAN 2024–25 figures; the procedure split, 75/25 runway split and go-around rates are assumptions.
- **Activity**: OSM shops, bus parks, markets, industrial and commercial land use, and major junctions. Bars, pubs and clubs form a separate nightlife layer.
- **Propagation**: FFT convolution of 1/r² point kernels (1/r for lines), with 9 dB first-row building screening and 0.016 dB/m excess attenuation.
- **Time**: hourly profiles per source give any hour of the day, plus Lden and Lnight.

Calibration check against published surveys: Kupondole 79 measured vs 77 modelled. Ring Road junctions are all >70 measured vs 80–84 modelled at peak. New Road is under-predicted (80 measured vs 67 modelled) because crowd noise isn't in OSM. Treat values as ±5 dB screening estimates.

Data © OpenStreetMap contributors (ODbL). Terrain: Mapzen Terrarium / AWS Open Data.
