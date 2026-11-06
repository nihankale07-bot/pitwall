import pandas as pd
path = r'C:\Users\Nihan\.vscode\pitwall\data\processed\9558\laps.parquet'
df = pd.read_parquet(path)
sub = df[(df['driver_number']==81) & (df['lap_number']>=20) & (df['lap_number']<=35)].sort_values('lap_number')
print(sub[['lap_number','lap_duration','compound','tyre_age']].to_string(index=False))

