from BIV_script import BeneficiarFounder
import csv
import polars as pl

if __name__=='__main__':
    company_file = '/app/company.tsv'
    legal_file = '/app/founder_legal.tsv'
    natural_file = '/app/founder_natural.tsv'
    
    founder = BeneficiarFounder(company_file, legal_file, natural_file)

    frame = founder.get_result_dataframe()

    frame = pl.from_pandas(frame)


    # Открываем выходной файл для записи
    with open('/app/output_file.tsv', 'w') as f:
        header = "company_id\togrn/natural_inn\tcompany_inn/last_name\tfull_name/first_name\tsecond_name\tshare_percent\n"
        f.write(header)
        
        # Группируем по полям компании
        grouped = frame.group_by(['company_id', 'ogrn', 'company_inn', 'full_name']).agg([
            pl.col('natural_inn'),
            pl.col('last_name'),
            pl.col('first_name'),
            pl.col('second_name'),
            pl.col('share_percent')
        ])
        
        # Проходим по каждой группе
        for group in grouped.iter_rows():
            # Формируем строку с данными компании
            company_id, ogrn, company_inn, full_name, *other_columns = group
            line1 = f"{company_id}\t{ogrn}\t{company_inn}\t{full_name}\t\t\n"
            
            # Записываем строку с данными компании
            f.write(line1)
            
            # Записываем данные по каждой строке группы
            for row in zip(*other_columns):
                natural_inn, last_name, first_name, second_name, share_percent = row
                line2 = f"\t{natural_inn}\t{last_name}\t{first_name}\t{second_name}\t{share_percent}\n"
                f.write(line2)
        
    # # Открываем выходной файл для записи
    # with open('output_file.tsv', 'w') as f:
    #     header = "company_id\togrn/natural_inn\tcompany_inn/last_name\tfull_name/first_name\tsecond_name\tshare_percent\n"
    #     f.write(header)
        
    #     # Группируем по полям компании
    #     grouped = frame.groupby(['company_id', 'ogrn', 'company_inn', 'full_name'])
    
    #     # Проходим по каждой группе
    #     for _, group in grouped:
    #         # Формируем строку с данными компании
    #         line1 = f"{group['company_id'].iloc[0]}\t{group['ogrn'].iloc[0]}\t{group['company_inn'].iloc[0]}\t{group['full_name'].iloc[0]}\t\t\n"
            
    #         # Записываем строку с данными компании
    #         f.write(line1)
            
    #         # Проходим по строкам группы, начиная с второй (где есть natural_inn)
    #         for _, row in group.iterrows():
    #             line2 = f"\t{row['natural_inn']}\t{row['last_name']}\t{row['first_name']}\t{row['second_name']}\t{row['share_percent']}\n"
    #             f.write(line2)