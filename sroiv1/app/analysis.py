from .models import Result, Stakeholder, Contribution
from collections import defaultdict

class ImpactAnalysis:
    def __init__(self, project_id):
        self.project_id = project_id
        self.total_input = self._calculate_total_input()
        
    def _calculate_total_input(self):
        """計算專案總投入，排除時間類型的貢獻"""
        contributions = Contribution.query.filter_by(project_id=self.project_id).all()
        return sum(float(c.resource_amount) for c in contributions 
                  if c.resource_type != 'time')
    
    def calculate_impact_score(self, result):
        """計算單一成果的影響力價值"""
        if not result.indicators or not result.impact_factors:
            return 0
            
        indicator = result.indicators[0]
        impact_factor = result.impact_factors[0]
        
        # 基本數值
        scale = indicator.scale_population
        weight = indicator.weight
        
        # 影響力因子
        deadweight = impact_factor.deadweight / 100
        displacement = impact_factor.displacement / 100
        attribution = impact_factor.attribution / 100
        drop_off = impact_factor.drop_off / 100
        
        # 檢查是否使用定價計算
        if indicator.pricing_amount:
            # 使用定價計算
            impact_value = (scale * indicator.pricing_amount) * (
                (1 - deadweight) *
                (1 - displacement) *
                (1 - drop_off) *
                (1 - attribution)
            )
        else:
            # 使用權重計算
            impact_value = (scale * weight) * (
                (1 - deadweight) *
                (1 - displacement) *
                (1 - drop_off) *
                (1 - attribution)
            )
        
        return impact_value
    
    def calculate_stakeholder_metrics(self):
        """計算每個利害關係人的指標"""
        stakeholder_metrics = defaultdict(lambda: {
            'name': '',
            'total_impact': 0,
            'results': [],
            'population': 0
        })
        
        # 獲取所有利害關係人
        stakeholders = Stakeholder.query.filter_by(project_id=self.project_id).all()
        
        # 先處理所有利害關係人，確保即使沒有成果也會顯示
        for stakeholder in stakeholders:
            # 獲取貢獻資料
            contribution = Contribution.query.filter_by(
                project_id=self.project_id,
                stakeholder_id=stakeholder.id
            ).first()
            
            # 初始化利害關係人資料
            stakeholder_metrics[stakeholder.id]['name'] = stakeholder.stakeholder_name
            if contribution:
                stakeholder_metrics[stakeholder.id]['contribution'] = {
                    'resource_type': contribution.resource_type,
                    'resource_amount': contribution.resource_amount
                }
        
        # 處理成果資料
        results = Result.query.filter_by(project_id=self.project_id).all()
        
        for result in results:
            stakeholder = result.stakeholder
            impact_score = self.calculate_impact_score(result)
            sroi = impact_score / self.total_input if self.total_input else 0
            
            # 檢查是否已經存在相同的成果
            existing_result = next(
                (r for r in stakeholder_metrics[stakeholder.id]['results'] 
                 if r['description'] == result.result_description),
                None
            )
            
            if not existing_result:
                stakeholder_metrics[stakeholder.id]['results'].append({
                    'description': result.result_description,
                    'impact_score': impact_score,
                    'sroi': sroi,
                    'event_chain': result.event_chain,
                    'indicator': {
                        'indicator_name': result.indicators[0].indicator_name if result.indicators else None,
                        'scale_population': result.indicators[0].scale_population if result.indicators else None,
                        'duration': result.indicators[0].duration if result.indicators else None,
                        'weight': result.indicators[0].weight if result.indicators else None,
                        'pricing_variable': result.indicators[0].pricing_variable if result.indicators else None,
                        'pricing_amount': result.indicators[0].pricing_amount if result.indicators else None,
                        'data_source': result.indicators[0].data_source if result.indicators else None
                    } if result.indicators else None,
                    'impact_factor': {
                        'deadweight': result.impact_factors[0].deadweight if result.impact_factors else None,
                        'displacement': result.impact_factors[0].displacement if result.impact_factors else None,
                        'attribution': result.impact_factors[0].attribution if result.impact_factors else None,
                        'drop_off': result.impact_factors[0].drop_off if result.impact_factors else None
                    } if result.impact_factors else None
                })
            
            metrics = stakeholder_metrics[stakeholder.id]
            metrics['total_impact'] += impact_score
            metrics['population'] += result.indicators[0].scale_population if result.indicators else 0
        
        # 計算每個利害關係人的總SROI
        for metrics in stakeholder_metrics.values():
            metrics['total_sroi'] = metrics['total_impact'] / self.total_input if self.total_input else 0
            
        return dict(stakeholder_metrics)
    
    def calculate_project_sroi(self):
        """計算專案總SROI"""
        results = Result.query.filter_by(project_id=self.project_id).all()
        
        # 計算總影響力價值
        total_impact_value = sum(self.calculate_impact_score(result) for result in results)
        
        # 計算總投入成本
        total_input = self._calculate_total_input()
        
        # 計算 SROI
        if total_input == 0:
            return 0
        return total_impact_value / total_input
    
    def get_project_summary(self):
        """獲取專案總體分析"""
        try:
            metrics = self.calculate_stakeholder_metrics()
            results = Result.query.filter_by(project_id=self.project_id).all()
            
            # 計算總影響力價值
            total_impact_value = 0
            for result in results:
                impact_value = self.calculate_impact_score(result)
                total_impact_value += impact_value
            
            # 新增：計算利害關係者人數分布
            stakeholder_population = []
            max_population = max(
                sum(
                    result.indicators[0].scale_population 
                    for result in results 
                    if result.stakeholder_id == stakeholder.id and result.indicators
                )
                for stakeholder in Stakeholder.query.filter_by(project_id=self.project_id).all()
            ) or 1  # 避免除零錯誤

            max_impact_value = max(
                sum(
                    self.calculate_impact_score(result)
                    for result in results
                    if result.stakeholder_id == stakeholder.id
                )
                for stakeholder in Stakeholder.query.filter_by(project_id=self.project_id).all()
            ) or 1  # 避免除零錯誤

            # 在泡泡圖資料計算中新增顏色
            COLORS = [
                '#FF6384', '#36A2EB', '#FFCE56', '#4BC0C0', '#9966FF',
                '#FF9F40', '#C9CBCF', '#4D5360', '#F7464A', '#46BFBD',
                '#FDB45C', '#949FB1', '#DCDCDC', '#8A2BE2', '#7FFF00'
            ]

            for i, stakeholder in enumerate(Stakeholder.query.filter_by(project_id=self.project_id).all()):
                population = sum(
                    result.indicators[0].scale_population 
                    for result in results 
                    if result.stakeholder_id == stakeholder.id and result.indicators
                )
                total_impact = sum(
                    self.calculate_impact_score(result)
                    for result in results
                    if result.stakeholder_id == stakeholder.id
                )
                
                # 將泡泡大小限制在 5-30 之間
                bubble_size = max(5, min(30, (population / max_population) * 30))
                
                stakeholder_population.append({
                    'name': stakeholder.stakeholder_name,
                    'population': population,
                    'total_impact': total_impact,
                    'x': population,  # x 軸使用人數
                    'y': total_impact, # y 軸使用總影響力價值
                    'r': bubble_size,  # 泡泡大小使用計算後的值
                    'color': COLORS[i % len(COLORS)]  # 分配顏色
                })
            
            # 將 results 轉換為字典形式
            results_dict = [
                {
                    'name': result.result_description[:30] + '...' if len(result.result_description) > 30 else result.result_description,
                    'sroi': self.calculate_impact_score(result) / self.total_input if self.total_input else 0,
                    'stakeholder': result.stakeholder.stakeholder_name,
                    'weight': result.indicators[0].weight if result.indicators else 0,
                    'event_chain': result.event_chain,
                    'indicator': {
                        'indicator_name': result.indicators[0].indicator_name if result.indicators else None,
                        'scale_population': result.indicators[0].scale_population if result.indicators else None,
                        'duration': result.indicators[0].duration if result.indicators else None,
                        'weight': result.indicators[0].weight if result.indicators else None,
                        'pricing_variable': result.indicators[0].pricing_variable if result.indicators else None,
                        'pricing_amount': result.indicators[0].pricing_amount if result.indicators else None,
                        'data_source': result.indicators[0].data_source if result.indicators else None
                    } if result.indicators else None,
                    'impact_factors': {
                        'deadweight': result.impact_factors[0].deadweight if result.impact_factors else None,
                        'displacement': result.impact_factors[0].displacement if result.impact_factors else None,
                        'attribution': result.impact_factors[0].attribution if result.impact_factors else None,
                        'drop_off': result.impact_factors[0].drop_off if result.impact_factors else None
                    } if result.impact_factors else None
                }
                for result in results
            ]
            
            # 計算每個利害關係者的平均影響力因子
            stakeholder_factors = defaultdict(lambda: {
                'name': '',
                'deadweight': 0,
                'displacement': 0,
                'attribution': 0,
                'drop_off': 0,
                'count': 0
            })
            
            for result in results:
                if result.impact_factors:
                    factor = result.impact_factors[0]
                    s_factors = stakeholder_factors[result.stakeholder.stakeholder_name]
                    s_factors['name'] = result.stakeholder.stakeholder_name
                    s_factors['deadweight'] += factor.deadweight
                    s_factors['displacement'] += factor.displacement
                    s_factors['attribution'] += factor.attribution
                    s_factors['drop_off'] += factor.drop_off
                    s_factors['count'] += 1
            
            # 計算平均值
            for s_factors in stakeholder_factors.values():
                if s_factors['count'] > 0:
                    s_factors['deadweight'] /= s_factors['count']
                    s_factors['displacement'] /= s_factors['count']
                    s_factors['attribution'] /= s_factors['count']
                    s_factors['drop_off'] /= s_factors['count']
            
            return {
                'total_impact': total_impact_value,
                'total_population': sum(int(m['population']) for m in metrics.values()),
                'project_sroi': self.calculate_project_sroi(),
                'total_impact_value': total_impact_value,
                'total_input': self._calculate_total_input(),
                'population_distribution': [
                    {
                        'name': m['name'],
                        'value': m['population'],
                        'percentage': (float(m['population']) / sum(float(m['population']) for m in metrics.values()) * 100) if metrics else 0
                    }
                    for m in metrics.values()
                ],
                'stakeholder_metrics': metrics,
                'result_types': [
                    {
                        'name': stakeholder.stakeholder_name,
                        'count': len([r for r in results if r.stakeholder_id == stakeholder.id])
                    }
                    for stakeholder in Stakeholder.query.filter_by(project_id=self.project_id).all()
                ],
                'results': results_dict,
                'stakeholder_population': stakeholder_population,  # 新增的利害關係者人數分布
                'stakeholder_factors': list(stakeholder_factors.values())
            }
        except Exception as e:
            print(f"Error in get_project_summary: {str(e)}")
            return {
                'total_impact': 0,
                'total_population': 0,
                'project_sroi': 0,
                'total_impact_value': 0,
                'total_input': 0,
                'population_distribution': [],
                'stakeholder_metrics': {},
                'result_types': [],
                'results': [],
                'stakeholder_population': [],  # 新增的利害關係者人數分布
                'stakeholder_factors': []
            } 