import pandas as pd
import matplotlib.pyplot as plt
from collections import deque
import polars as pl
import networkx as nx
from networkx.drawing.nx_agraph import graphviz_layout
from networkx.drawing import nx_pydot  # Импортируем правильно

class BeneficiarFounder():
    '''
    Usage: 
    Initialize class with paths to tsv's 
    If only graph is required call .build_full_graph()
    If need a drawing of graph call .draw_graph(indexes), reccomended no more than 10 nodes in indexes
    To have final pandas dataframe use .get_result_dataframe()
    
    '''
    
    def __init__(self, company_tsv_location, legal_tsv_location, natural_tsv_location): 
        self.company = pd.DataFrame()
        self.founder_legal = pd.DataFrame()
        self.founder_natural = pd.DataFrame()
        self.company_cleared = pd.DataFrame()
        self.founder_legal_cleared = pd.DataFrame()
        self.founder_natural_cleared = pd.DataFrame()
        self.natural_owners_dict = {}
        self.legal_owners_dict = {}

        self._load_data(company_tsv_location, legal_tsv_location, natural_tsv_location)
        self._clean_data()
        self._init_owners_dict()

    def _load_data(self, company_tsv_location, legal_tsv_location, natural_tsv_location):
        
        self.company = pd.read_csv(company_tsv_location, sep='\t',     dtype={
                "id": "string",   
                "ogrn": "string", 
                "inn": "string",   
                "full_name": "string",   
            })
        self.founder_legal = pd.read_csv(legal_tsv_location, sep='\t',dtype={
                "id": "string",  
                "company_id": "string",
                "ogrn": "string",  
                "inn": "string",  
                "full_name": "string", 
                "share": "float", 
                "share_percent": "float", 
        
            })
        self.founder_natural = pd.read_csv(natural_tsv_location, sep='\t', dtype={
            
                "id": "string", 
                "company_id": "string",
                "inn": "string", 
                "last_name": "string", 
                "first_name": "string", 
                "second_name": "string", 
                "share": "float",  
                "share_percent": "float", 
            })

    def _restore_share_percent(self, df_legal, df_natural):
        """
        Функция для восстановления пропущенных значений share_percent для учредителей
        компании на основе значений share.
    
        Аргументы:
        df_legal (DataFrame): DataFrame для юридических лиц с колонками id, company_id, share, share_percent.
        df_natural (DataFrame): DataFrame для физических лиц с колонками id, company_id, share, share_percent.
    
        Возвращает:
        tuple: два DataFrame — обновленные df_legal и df_natural.
        
        """
        
        # Объединяем оба DataFrame, чтобы учесть всех учредителей компании
        df_all = pd.concat([df_legal, df_natural], ignore_index=True)
        
        # Исключаем компании с `NaN` или нулевыми значениями в `share`
        valid_companies = (
            df_all.groupby('company_id')['share']
            .apply(lambda x: x.notna().all() and (x > 0).all())
        )
        valid_companies = valid_companies[valid_companies].index
        df_all = df_all[df_all['company_id'].isin(valid_companies)].copy()
        
        # Вычисляем сумму долей для каждой компании
        total_share_by_company = df_all.groupby('company_id')['share'].transform('sum')
        
        # Восстанавливаем share_percent только для строк с NaN в этом поле
        df_all['share_percent_restored'] = (
            df_all['share'] / total_share_by_company
        )
        
        # Обновляем оригинальное share_percent
        df_all['share_percent'] = df_all['share_percent'].fillna(df_all['share_percent_restored'])
        df_all.drop(columns=['share_percent_restored'], inplace=True)
        
        # Возвращаем только те строки, которые были в изначальных DataFrame
        df_legal_updated = df_all[df_all['uid'].isin(df_legal['uid'])].copy()
        df_natural_updated = df_all[df_all['uid'].isin(df_natural['uid'])].copy()
        
        return df_legal_updated, df_natural_updated

    def _clean_data(self, ): 
        """
        Функция инициализации для подготовки данных к последующим вычислениям

        1. Дропает na значения 
        2. Делает id уникальными для legal и natural
        3. Восстанавливает проценты используя метод _restore_share_percent
        4. Округляет полученные значения share_percent до 4 знаков
        
        """
        self.company = self.company.dropna()
        self.founder_legal = self.founder_legal.dropna(subset=['ogrn', 'inn'])

        self.company_cleared = self.company.drop(['ogrn', 'inn', 'full_name'], axis=1) 
        self.founder_legal_cleared = self.founder_legal.drop(['ogrn', 'inn', 'full_name'], axis=1)
        self.founder_natural_cleared = self.founder_natural.drop(['inn', 'last_name', 'first_name', 'second_name',], axis=1)

        self.company_cleared['uid'] = 'cp_'+ self.company_cleared['id']

        self.founder_legal_cleared['uid'] = 'cp_'+ self.founder_legal_cleared['id']
        self.founder_legal_cleared['company_id'] = 'cp_'+ self.founder_legal_cleared['company_id']

        self.founder_natural_cleared['uid'] = 'nt_'+ self.founder_natural_cleared['id']
        self.founder_natural_cleared['company_id'] = 'cp_'+ self.founder_natural_cleared['company_id']

        self.founder_legal_cleared, self.founder_natural_cleared = self._restore_share_percent(self.founder_legal_cleared, self.founder_natural_cleared)

        self.founder_legal_cleared['share_percent'] = round(self.founder_legal_cleared['share_percent'], 4)
        self.founder_natural_cleared['share_percent'] = round(self.founder_natural_cleared['share_percent'], 4)

        return self.founder_legal_cleared, self.founder_natural_cleared

    def _init_owners_dict(self, ): 
        '''
        Функци инициализирует два словаря владений, которые в последствии будут 
        использоваться при построении графов. 
        Ключ - id компании
        Значение - все овнеры

        Для ускорения вычислений использованы DataFrame от библиотеки Polars.
        
        '''
                
        founder_natural_cleared_pl = pl.from_pandas(self.founder_natural_cleared)
        founder_legal_cleared_pl = pl.from_pandas(self.founder_legal_cleared)
        
        self.natural_owners_dict = {
            row['company_id']: row['owners']
            for row in founder_natural_cleared_pl
            .group_by('company_id')
            .agg([pl.struct(['uid', 'share_percent']).alias('owners')])
            .to_dicts()
        }
        
        self.legal_owners_dict = {
            row['company_id']: row['owners']
            for row in founder_legal_cleared_pl
            .group_by('company_id')
            .agg([pl.struct(['uid', 'share_percent']).alias('owners')])
            .to_dicts()
        }
        

    def _build_graph_for_node(self, company_id, company_df, founder_legal_df, founder_natural_df, G=None):
        '''        
        Функция циклично вычисляет граф-дерево владений для определенной компании. 
        Была использована двусторонняя очередь в качестве структуры данных для значительного ускорения
        вычислений. (Вычисление в обычной очереди реализованной через список - О(n), вычисления в deque - О(1))
    
        '''
        
        if G is None:
            G = nx.Graph()
        
        queue = deque([company_id])
    
        while queue:
            current_company = queue.popleft()
            
            # Добавляем компанию в граф
            G.add_node(current_company, type="company")
            
            # Извлекаем владельцев
            natural_owners = self.natural_owners_dict.get(current_company, [])
            legal_owners = self.legal_owners_dict.get(current_company, [])
            
            for owner in natural_owners:
                owner_id = owner['uid']
                G.add_node(owner_id, type="natural")
                G.add_edge(current_company, owner_id, weight=owner['share_percent'])
            
            for owner in legal_owners:
                owner_id = owner['uid']
                G.add_node(owner_id)
                G.add_edge(current_company, owner_id, weight=owner['share_percent'])
                queue.append(owner_id)  # Добавляем владельца в очередь для дальнейшего обхода
        
        return G
    

    def build_full_graph(self, ): 
        '''
        Функция для построения полного графа. 
        
        '''

        G = nx.Graph() 
        for idx, row in self.company_cleared.iterrows():
            company_id = row['uid']
            G = self._build_graph_for_node(company_id, self.company_cleared, self.founder_legal_cleared, self.founder_natural_cleared, G)
            
        return G
            
        
    def draw_graph(self, draw_indexes): 
        """
        Строит и рисует граф владения для заданных индексов.
        
        """
        G = nx.Graph()  
        
        # Строим граф для каждой компании из company_df
        for idx, row in self.company_cleared[draw_indexes[0] : draw_indexes[1]].iterrows():
            company_id = row['uid']
            G = self._build_graph_for_node(company_id, self.company_cleared, self.founder_legal_cleared, self.founder_natural_cleared, G)
    
        # Получаем позиции узлов с использованием layout
        pos = nx_pydot.graphviz_layout(G, prog="dot")
        
        # Настройка рисования графа
        plt.figure(figsize=(12, 12))
        node_colors = [
            'skyblue' if G.nodes[node].get('type') == 'company' else 
            'lightcoral' 
            for node in G.nodes
        ]
        nx.draw_networkx_nodes(G, pos, node_size=2000, node_color=node_colors)
        nx.draw_networkx_labels(G, pos, font_size=8)
        nx.draw_networkx_edges(G, pos, width=2, alpha=0.6, edge_color="gray")
        
        # Рисуем рёбра с весами
        edge_labels = nx.get_edge_attributes(G, 'weight')
        nx.draw_networkx_edge_labels(G, pos, edge_labels=edge_labels)
        
        # Показываем граф
        plt.title("Ownership Graph for Companies")
        plt.axis("off")
        plt.show()


    

    def _calculate_final_shares(self, G, start_nodes):
        """
        Для каждой начальной вершины находит конечные ноды (с типом 'natural') 
        и считает долю владения на основе произведения весов рёбер.
        Возвращает словарь формата:
        
        {
            'ВЕРШИНА': {'НОДА1': доля, 'НОДА2': доля}
        }
        In: G - граф, start_nodes - начальные вершины( python.tsv)
        Out: dict results
        
        """
        results = {}
    
        def dfs(node, current_share, visited):
            """
            Рекурсивно обходит граф в глубину, вычисляя долю владения
            через произведение весов рёбер.
            """
            if node in visited:
                return {}
            visited.add(node)
    
            # Если дошли до конечной ноды (natural), возвращаем её с текущей долей
            if G.nodes[node]['type'] == 'natural':
                return {node: current_share}
    
            # обходим всех соседей
            shares = {}
            for neighbor in G.neighbors(node):
                edge_weight = G[node][neighbor].get('weight', 1)
                sub_shares = dfs(neighbor, current_share * edge_weight, visited.copy())
    
                # Суммируем доли для повторяющихся конечных нод
                for natural_node, share in sub_shares.items():
                    if natural_node in shares:
                        shares[natural_node] += share
                    else:
                        shares[natural_node] = share
    
            return shares
    
        # Обрабатываем только начальные вершины
        for start_node in start_nodes:
            results[start_node] = dfs(start_node, 1, set())
    
        return results


    def _filter_ownership_shares(self, ownership_shares, threshold=0.25):
        """
        Фильтрует конечные узлы (natural) в словаре владений, оставляя только те,
        чья доля больше заданного порога (threshold).
        
        """
        
        filtered_shares = {}
        for node, shares in ownership_shares.items():
            # Фильтруем вложенные словари по значению (доля > threshold)
            filtered_shares[node] = {
                natural_node: share
                for natural_node, share in shares.items()
                if share > threshold
            }
        return filtered_shares


        
    def _find_beneficiars(self, G): 
        '''
        Вспомогательная функция, соединяющая _calculate_final_shares и _filter_ownership_shares в одну
        
        '''
        
        shares = self._calculate_final_shares(G, self.company_cleared['uid'].tolist())
        benef = self._filter_ownership_shares(shares, threshold=0.25)
        
        return benef
        
    def _convert_to_dataframe(self, ownership_shares):
        """
        Конвертирует словарь владений в Pandas DataFrame с колонками:
        'Вершина', 'Нода', 'Доля'.
        In: словарь владений ownership_shares вида  {'ВЕРШИНА': {'НОДА1': доля, 'НОДА2': доля} }
        Out: pandas DF с столбцами uid_cp, uid_nt, share_percentage
        
        """
        
        rows = []
        for node, shares in ownership_shares.items():
            for natural_node, share in shares.items():
                rows.append({'uid_cp': node, 'uid_nt': natural_node, 'share_percentage': share})
    
        # Создаём DataFrame
        df = pd.DataFrame(rows)
        
        # Сортируем по вершине и доле
        df = df.sort_values(by=['uid_nt', 'share_percentage'], ascending=[True, False])
        return df

        
    def get_result_dataframe(self, ): 
        '''
        Использует функцию build_full_graph для построения графа. 
        Определяет бенефициаров в словаре владений
        Путём добавления данных по индексам из изначальных таблиц строит результирующий датафрейм. 
        
        '''

        # Получаем граф владения
        G = self.build_full_graph()
        # Определяем словарь владений, сортированный до бенефициаров и переводим его во фрейм 
        benef = self._find_beneficiars(G)
        df = self._convert_to_dataframe(benef)

        #Мерджим индексы uid_cp с очищенным датафреймом для получения id
        self.company_cleared['uid_cp'] = self.company_cleared['uid']
        result = df.merge(self.company_cleared, how='left', on='uid_cp').drop(['uid_cp', 'uid'], axis=1)
        # по id мерджим фрейм с итоговым датасетом
        result = result.merge(self.company, how='left', on='id')

        #Аналогично проделываем для founders
        self.founder_natural_cleared['uid_nt'] = self.founder_natural_cleared['uid']
        result = result.merge(self.founder_natural_cleared, how='left', on='uid_nt').drop(['company_id', 'share', 'share_percentage', 'uid_nt', 'uid',],axis=1)
        self.founder_natural['id_y'] = self.founder_natural['id']
        result = result.merge(self.founder_natural, how='left', on='id_y').drop(['id_y', 'share_percent_y', 'id', 'company_id', 'share'],axis=1)

        # для правильного расположения столбцов
        result['share_percent'] = result['share_percent_x']
        result = result.drop(['share_percent_x'],axis=1)

        #Определяем необходимые названия столбцов
        result = result.rename(columns={'id_x': 'company_id', 'inn_x': 'company_inn', 'inn_y': 'natural_inn'})
        
        return result

