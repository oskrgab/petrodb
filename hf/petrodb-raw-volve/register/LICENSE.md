# Licence: Norwegian Licence for Open Government Data (NLOD)

The files in this folder are a snapshot of the public wellbore register kept
by the Norwegian Offshore Directorate (formerly the Norwegian Petroleum
Directorate), taken from its FactPages: the CSV exports of all development
wellbores and all exploration wellbores on the Norwegian continental shelf.

Contains data under the Norwegian licence for Open Government data (NLOD)
distributed by the Norwegian Offshore Directorate.

- Licence: <https://data.norge.no/nlod/en>
- Source: <https://factpages.sodir.no/>

| File | Content |
| --- | --- |
| `wellbore_development_all.csv` | Every development wellbore in the register, as exported. |
| `wellbore_exploration_all.csv` | Every exploration wellbore in the register, as exported. |
| `download_date.txt` | The date (UTC) the two exports were downloaded. |

The exports are stored unchanged. They cover the whole continental shelf, not
only Volve; the petrodb pipeline selects the Volve wellbores from them.
