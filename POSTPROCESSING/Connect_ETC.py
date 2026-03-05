import pandas as pd

#run ~/TRACKING/KATJA/POSTPROCESSING/Connect_ETC.py

simulations = ['UBI', 'UBB', 'ERA5', 'UBG', 'UBD', 'UBH', 'UBE', 'UBF']
hist_future_map = {'UBG': 'UBD', 'UBH': 'UBE', 'UBI': 'UBF'}

for sim in simulations:
    
    if sim in ['UBG', 'UBH']:
        start_year = 2015
        end_year = 2100
    elif sim == 'UBI':
        start_year = 2015
        end_year = 2098
    elif sim in ['UBB', 'ERA5']:
        start_year = 1979
        end_year = 2023
    else:
        start_year = 1979
        end_year = 2014
        
    print(f"Processing simulation: {sim}")

    dfs = []
    for year in range(start_year, end_year + 1):
        df = pd.read_csv(
        f'/home/vdemeyer/projects/rrg-gachon/vdemeyer/TRACKING/KATJA/OUTPUTS/{sim}_psl_smoothed_400km_12h_1005hPa_{year}_1month.txt',
        sep=r'\s+', header=14, engine='python',
        names=['storm','point','i','j','date','lat','lon','pressure']
        )
        df['date'] = pd.to_datetime(df['date'].astype(str), format='%Y%m%d%H', errors='coerce')
        dfs.append(df)

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