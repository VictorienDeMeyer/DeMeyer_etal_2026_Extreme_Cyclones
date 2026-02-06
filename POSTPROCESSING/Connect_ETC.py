import pandas as pd

#run ~/TRACKING/KATJA/POSTPROCESSING/Connect_ETC.py

simulations = ['UBI', 'UBB', 'ERA5', 'UBG', 'UBD', 'UBH', 'UBE', 'UBF']
hist_future_map = {'UBG': 'UBD', 'UBH': 'UBE', 'UBI': 'UBF'}

for sim in simulations:
        
    print(f"Processing simulation: {sim}")
    if sim in hist_future_map:
        hist_sim = hist_future_map[sim]
        dfs = []
        periods_hist = []
        hist_periods = ['1979-1979', '1980-1989', '1990-1999', '2000-2009']
        periods_hist.extend((hist_sim, p) for p in hist_periods)
        for start in range(2010, 2100, 10):
            end = start + 9
            if sim == 'UBI' and start == 2090:
                end = 2098
            periods_hist.append((sim, f"{start}-{end}"))
        if sim != 'UBI':
            periods_hist.append((sim, '2100-2100'))

        for idx, (sim_name, period) in enumerate(periods_hist):
            try:
                df = pd.read_csv(
                    f'/home/vdemeyer/projects/rrg-gachon/vdemeyer/TRACKING/KATJA/OUTPUTS/{sim_name}_psl_smoothed_400km_12h_1005hPa_{period}_1month.txt',
                    sep=r'\s+', header=14, engine='python',
                    names=['storm','point','i','j','date','lat','lon','pressure']
                )
                df['date'] = pd.to_datetime(df['date'].astype(str), format='%Y%m%d%H', errors='coerce')
                dfs.append(df)
            except FileNotFoundError:
                raise FileNotFoundError(f"File not found for simulation '{sim_name}' and period '{period}'")

    elif sim == 'UBB':
        df1 = pd.read_csv(f'/home/vdemeyer/projects/rrg-gachon/vdemeyer/TRACKING/KATJA/OUTPUTS/{sim}_psl_smoothed_400km_12h_1005hPa_1979-1979_1month.txt', sep=r'\s+', header=14, engine='python', names=['storm','point','i','j','date','lat','lon','pressure'])
        df1['date'] = pd.to_datetime(df1['date'].astype(str), format='%Y%m%d%H', errors='coerce')

        df2 = pd.read_csv(f'/home/vdemeyer/projects/rrg-gachon/vdemeyer/TRACKING/KATJA/OUTPUTS/{sim}_psl_smoothed_400km_12h_1005hPa_1980-1989_1month.txt', sep=r'\s+', header=14, engine='python', names=['storm','point','i','j','date','lat','lon','pressure'])
        df2['date'] = pd.to_datetime(df2['date'].astype(str), format='%Y%m%d%H', errors='coerce')

        df3 = pd.read_csv(f'/home/vdemeyer/projects/rrg-gachon/vdemeyer/TRACKING/KATJA/OUTPUTS/{sim}_psl_smoothed_400km_12h_1005hPa_1990-1999_1month.txt', sep=r'\s+', header=14, engine='python', names=['storm','point','i','j','date','lat','lon','pressure'])
        df3['date'] = pd.to_datetime(df3['date'].astype(str), format='%Y%m%d%H', errors='coerce')

        df4 = pd.read_csv(f'/home/vdemeyer/projects/rrg-gachon/vdemeyer/TRACKING/KATJA/OUTPUTS/{sim}_psl_smoothed_400km_12h_1005hPa_2000-2009_1month.txt', sep=r'\s+', header=14, engine='python', names=['storm','point','i','j','date','lat','lon','pressure'])
        df4['date'] = pd.to_datetime(df4['date'].astype(str), format='%Y%m%d%H', errors='coerce')

        df5 = pd.read_csv(f'/home/vdemeyer/projects/rrg-gachon/vdemeyer/TRACKING/KATJA/OUTPUTS/{sim}_psl_smoothed_400km_12h_1005hPa_2010-2019_1month.txt', sep=r'\s+', header=14, engine='python', names=['storm','point','i','j','date','lat','lon','pressure'])
        df5['date'] = pd.to_datetime(df5['date'].astype(str), format='%Y%m%d%H', errors='coerce')

        df6 = pd.read_csv(f'/home/vdemeyer/projects/rrg-gachon/vdemeyer/TRACKING/KATJA/OUTPUTS/{sim}_psl_smoothed_400km_12h_1005hPa_2020-2023_1month.txt', sep=r'\s+', header=14, engine='python', names=['storm','point','i','j','date','lat','lon','pressure'])
        df6['date'] = pd.to_datetime(df6['date'].astype(str), format='%Y%m%d%H', errors='coerce')

        dfs = [df1, df2, df3, df4, df5, df6]

    elif sim == 'ERA5':
        dfs = []
        for year in range(1979, 2024):
            df = pd.read_csv(
            f'/home/vdemeyer/projects/rrg-gachon/vdemeyer/TRACKING/KATJA/OUTPUTS/{sim}_psl_smoothed_400km_12h_1005hPa_{year}_1month.txt',
            sep=r'\s+', header=14, engine='python',
            names=['storm','point','i','j','date','lat','lon','pressure']
            )
            df['date'] = pd.to_datetime(df['date'].astype(str), format='%Y%m%d%H', errors='coerce')
            dfs.append(df)
            
    else:
        df1 = pd.read_csv(f'/home/vdemeyer/projects/rrg-gachon/vdemeyer/TRACKING/KATJA/OUTPUTS/{sim}_psl_smoothed_400km_12h_1005hPa_1979-1979_1month.txt', sep=r'\s+', header=14, engine='python', names=['storm','point','i','j','date','lat','lon','pressure'])
        df1['date'] = pd.to_datetime(df1['date'].astype(str), format='%Y%m%d%H', errors='coerce')

        df2 = pd.read_csv(f'/home/vdemeyer/projects/rrg-gachon/vdemeyer/TRACKING/KATJA/OUTPUTS/{sim}_psl_smoothed_400km_12h_1005hPa_1980-1989_1month.txt', sep=r'\s+', header=14, engine='python', names=['storm','point','i','j','date','lat','lon','pressure'])
        df2['date'] = pd.to_datetime(df2['date'].astype(str), format='%Y%m%d%H', errors='coerce')

        df3 = pd.read_csv(f'/home/vdemeyer/projects/rrg-gachon/vdemeyer/TRACKING/KATJA/OUTPUTS/{sim}_psl_smoothed_400km_12h_1005hPa_1990-1999_1month.txt', sep=r'\s+', header=14, engine='python', names=['storm','point','i','j','date','lat','lon','pressure'])
        df3['date'] = pd.to_datetime(df3['date'].astype(str), format='%Y%m%d%H', errors='coerce')

        df4 = pd.read_csv(f'/home/vdemeyer/projects/rrg-gachon/vdemeyer/TRACKING/KATJA/OUTPUTS/{sim}_psl_smoothed_400km_12h_1005hPa_2000-2009_1month.txt', sep=r'\s+', header=14, engine='python', names=['storm','point','i','j','date','lat','lon','pressure'])
        df4['date'] = pd.to_datetime(df4['date'].astype(str), format='%Y%m%d%H', errors='coerce')

        df5 = pd.read_csv(f'/home/vdemeyer/projects/rrg-gachon/vdemeyer/TRACKING/KATJA/OUTPUTS/{sim}_psl_smoothed_400km_12h_1005hPa_2010-2014_1month.txt', sep=r'\s+', header=14, engine='python', names=['storm','point','i','j','date','lat','lon','pressure'])
        df5['date'] = pd.to_datetime(df5['date'].astype(str), format='%Y%m%d%H', errors='coerce')

        dfs = [df1, df2, df3, df4, df5]

    # Fusionner les DataFrames et supprimer les doublons
    for i in range(len(dfs) - 1):
        df1 = dfs[i]
        df2 = dfs[i + 1]

        max_storm_df1 = df1['storm'].max()
        df2.loc[:, 'storm'] = df2['storm'] + max_storm_df1 #je fais en sorte que les indices des storms de df2 commence à la suite de ceux de df1

        merged_df = df1.merge(df2, on=['date', 'lat', 'lon', 'pressure'], suffixes=('_df1', '_df2')) #je fais une jointure sur les colonnes date, lat, lon et pressure
        duplicate_storms = merged_df[['storm_df1', 'storm_df2']].drop_duplicates() #je récupère les storms qui sont présents dans les deux dataframes

        for _, row in duplicate_storms.iterrows(): #je parcours les storms en doublon
            storm_df1 = row['storm_df1']
            storm_df2 = row['storm_df2']

            group_df1 = df1[df1['storm'] == storm_df1]
            group_df2 = df2[df2['storm'] == storm_df2]

            if len(group_df1) > len(group_df2): #je garde le groupe qui a le plus de points
                df2 = df2[df2['storm'] != storm_df2]
            else:
                df1 = df1[df1['storm'] != storm_df1]

        dfs[i + 1] = pd.concat([df1, df2]).reset_index(drop=True) #je fusionne les deux dataframes une fois que les doublons ont été supprimés

    merged_df_final = dfs[i + 1] #je récupère le dernier dataframe qui correspond à la fusion de tous les dataframes

    storm_start_dates = merged_df_final.groupby('storm')['date'].min().reset_index() #je récupère la date de début de chaque storm
    storm_start_dates = storm_start_dates.sort_values(by='date').reset_index(drop=True) #je trie les storms par date de début
    storm_order = storm_start_dates['storm'].tolist() #je récupère l'ordre des storms dans un tableau
    merged_df_final['storm'] = pd.Categorical(merged_df_final['storm'], categories=storm_order, ordered=True) #je transforme la colonne storm en catégorie ordonnée
    merged_df_final = merged_df_final.sort_values(by=['storm', 'date'], ascending=[True, True]).reset_index(drop=True) #je trie le dataframe par date mais la storm 2 peut être devant la 1 à ce stade
    reindex_dict = {old: new for new, old in enumerate(storm_order, start=1)} #je crée un dictionnaire pour réindexer les storms via le tableau créé
    merged_df_final['storm'] = merged_df_final['storm'].map(reindex_dict) #je réindexe les storms, la 1 est maintenant la plus récente par son début
    
    if sim in hist_future_map: merged_df_final = merged_df_final[merged_df_final['date'] != pd.Timestamp('2100-12-31 00:00:00')]

    merged_df_final.to_csv(f'/home/vdemeyer/projects/rrg-gachon/vdemeyer/TRACKING/KATJA/OUTPUTS/{sim}_psl_smooth_400km_12h_1005hPa.txt', sep=' ', index=False)
    print(f"Finished processing simulation: {sim}")