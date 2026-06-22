import pandas as pd

#run ~/TRACKING/KATJA/POSTPROCESSING/connect_ETCs.py

simulations = ['ERA5', 'UBB', 'UBD', 'UBE', 'UBF', 'UBG', 'UBH', 'UBI']

for sim in simulations:

    if sim in ['UBG', 'UBH', 'UBI']:
        start_year = 2063
        end_year = 2097
    else:
        start_year = 1980
        end_year = 2014

    print(f"Processing simulation: {sim}")

    dfs = []

    for year in range(start_year, end_year + 1):
        df = pd.read_csv(
        f'/home/vdemeyer/projects/rrg-gachon/vdemeyer/{sim}/STORM_RELATED/TRACK/{sim}_psl_smoothed_400km_24h_1000hPa_{year}_1month.txt',
        sep=r'\\s+', header=14, engine='python',
        names=['storm','point','i','j','date','lat','lon','pressure']
        )
        df['date'] = pd.to_datetime(df['date'].astype(str), format='%Y%m%d%H', errors='coerce')
        dfs.append(df)

    for i in range(len(dfs) - 1):
        df1 = dfs[i]
        df2 = dfs[i + 1]

        max_storm_df1 = df1['storm'].max()
        df2.loc[:, 'storm'] = df2['storm'] + max_storm_df1

        merged_df = df1.merge(df2, on=['date', 'lat', 'lon', 'pressure'], suffixes=('_df1', '_df2'))
        duplicate_storms = merged_df[['storm_df1', 'storm_df2']].drop_duplicates()

        for _, row in duplicate_storms.iterrows():
            storm_df1 = row['storm_df1']
            storm_df2 = row['storm_df2']

            group_df1 = df1[df1['storm'] == storm_df1]
            group_df2 = df2[df2['storm'] == storm_df2]

            if len(group_df1) > len(group_df2):
                df2 = df2[df2['storm'] != storm_df2]
            else:
                df1 = df1[df1['storm'] != storm_df1]

        dfs[i + 1] = pd.concat([df1, df2]).reset_index(drop=True)

    merged_df_final = dfs[i + 1]

    merged_df_final = merged_df_final[
        (merged_df_final['date'] >= pd.Timestamp(f'{start_year}-01-01')) &
        (merged_df_final['date'] <= pd.Timestamp(f'{end_year}-12-31 23:59:59'))
    ].copy()

    storm_start_dates = merged_df_final.groupby('storm')['date'].min().reset_index() #je récupère la date de début de chaque storm
    storm_start_dates = storm_start_dates.sort_values(by='date').reset_index(drop=True) #je trie les storms par date de début
    storm_order = storm_start_dates['storm'].tolist() #je récupère l'ordre des storms dans un tableau
    merged_df_final['storm'] = pd.Categorical(merged_df_final['storm'], categories=storm_order, ordered=True) #je transforme la colonne storm en catégorie ordonnée
    merged_df_final = merged_df_final.sort_values(by=['storm', 'date'], ascending=[True, True]).reset_index(drop=True) #je trie le dataframe par date mais la storm 2 peut être devant la 1 à ce stade
    reindex_dict = {old: new for new, old in enumerate(storm_order, start=1)} #je crée un dictionnaire pour réindexer les storms via le tableau créé
    merged_df_final['storm'] = merged_df_final['storm'].map(reindex_dict) #je réindexe les storms, la 1 est maintenant la plus récente par son début

    merged_df_final.to_csv(f'/home/vdemeyer/projects/rrg-gachon/vdemeyer/{sim}/STORM_RELATED/TRACK/{sim}_psl_smooth_400km_24h_1000hPa.txt', sep=' ', index=False)
    print(f"Finished processing simulation: {sim}")
