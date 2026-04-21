#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
电池阻抗测试系统 - 机器学习预测模型
实现基于阻抗参数的电池性能预测功能
"""

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.linear_model import LinearRegression
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import mean_squared_error, r2_score
import joblib
import os
from datetime import datetime
import logging

class BatteryPerformancePredictor:
    """电池性能预测器"""
    
    def __init__(self):
        self.models = {}
        self.scalers = {}
        self.model_metadata = {}
        self.logger = logging.getLogger(__name__)
        
    def prepare_features(self, rs_values, rct_values, voltages=None, temperatures=None, battery_types=None):
        """准备特征数据"""
        features = []
        
        # 基础阻抗特征
        features.extend([
            np.array(rs_values),
            np.array(rct_values),
            np.array(rs_values) + np.array(rct_values),  # 总阻抗
            np.array(rct_values) / np.array(rs_values),   # 阻抗比
        ])
        
        # 电压特征
        if voltages is not None:
            features.append(np.array(voltages))
        else:
            features.append(np.full(len(rs_values), 3.2))  # 默认电压
            
        # 温度特征
        if temperatures is not None:
            features.append(np.array(temperatures))
        else:
            features.append(np.full(len(rs_values), 25.0))  # 默认温度
            
        # 电池类型特征（独热编码）
        if battery_types is not None:
            type_mapping = {'LFP': 0, 'NCM': 1, 'LTO': 2, 'OTHER': 3}
            type_features = [type_mapping.get(bt, 3) for bt in battery_types]
            features.append(np.array(type_features))
        else:
            features.append(np.full(len(rs_values), 0))  # 默认LFP
            
        return np.column_stack(features)
    
    def generate_synthetic_data(self, n_samples=1000):
        """生成合成训练数据"""
        np.random.seed(42)
        
        # 生成阻抗数据
        rs_values = np.random.normal(0.05, 0.01, n_samples)  # Rs: 0.03-0.07 Ω
        rs_values = np.clip(rs_values, 0.02, 0.1)
        
        rct_values = np.random.normal(0.02, 0.005, n_samples)  # Rct: 0.01-0.03 Ω
        rct_values = np.clip(rct_values, 0.005, 0.05)
        
        # 生成其他特征
        voltages = np.random.normal(3.2, 0.1, n_samples)
        voltages = np.clip(voltages, 3.0, 3.4)
        
        temperatures = np.random.normal(25, 5, n_samples)
        temperatures = np.clip(temperatures, 15, 35)
        
        battery_types = np.random.choice(['LFP', 'NCM', 'LTO'], n_samples, p=[0.6, 0.3, 0.1])
        
        # 准备特征
        X = self.prepare_features(rs_values, rct_values, voltages, temperatures, battery_types)
        
        # 生成目标变量（基于物理关系的合成数据）
        # 容量预测（mAh）
        base_capacity = 3000
        capacity_factor = 1 - (rs_values - 0.03) * 10 - (rct_values - 0.015) * 20
        capacity_factor += (voltages - 3.2) * 0.1 + np.random.normal(0, 0.05, n_samples)
        capacity = base_capacity * np.clip(capacity_factor, 0.7, 1.2)
        
        # 循环寿命预测
        base_cycles = 2000
        cycle_factor = 1 - (rs_values - 0.03) * 15 - (rct_values - 0.015) * 25
        cycle_factor += np.random.normal(0, 0.1, n_samples)
        cycle_life = base_cycles * np.clip(cycle_factor, 0.5, 1.5)
        
        # 温度性能系数
        temp_performance = 1 - abs(temperatures - 25) * 0.01 + np.random.normal(0, 0.02, n_samples)
        temp_performance = np.clip(temp_performance, 0.8, 1.1)
        
        return X, {
            'capacity': capacity,
            'cycle_life': cycle_life,
            'temp_performance': temp_performance
        }
    
    def train_capacity_model(self, X, y_capacity):
        """训练容量预测模型"""
        self.logger.info("开始训练容量预测模型...")
        
        # 数据分割
        X_train, X_test, y_train, y_test = train_test_split(X, y_capacity, test_size=0.2, random_state=42)
        
        # 特征缩放
        scaler = StandardScaler()
        X_train_scaled = scaler.fit_transform(X_train)
        X_test_scaled = scaler.transform(X_test)
        
        # 训练模型
        model = RandomForestRegressor(n_estimators=100, random_state=42)
        model.fit(X_train_scaled, y_train)
        
        # 评估模型
        y_pred = model.predict(X_test_scaled)
        rmse = np.sqrt(mean_squared_error(y_test, y_pred))
        r2 = r2_score(y_test, y_pred)
        
        # 交叉验证
        cv_scores = cross_val_score(model, X_train_scaled, y_train, cv=5, scoring='r2')
        
        # 保存模型
        self.models['capacity'] = model
        self.scalers['capacity'] = scaler
        self.model_metadata['capacity'] = {
            'rmse': rmse,
            'r2': r2,
            'cv_mean': cv_scores.mean(),
            'cv_std': cv_scores.std(),
            'trained_at': datetime.now().isoformat(),
            'n_samples': len(X_train)
        }
        
        self.logger.info(f"容量预测模型训练完成 - RMSE: {rmse:.2f}, R²: {r2:.3f}")
        return rmse, r2
    
    def train_cycle_life_model(self, X, y_cycle_life):
        """训练循环寿命预测模型"""
        self.logger.info("开始训练循环寿命预测模型...")
        
        # 数据分割
        X_train, X_test, y_train, y_test = train_test_split(X, y_cycle_life, test_size=0.2, random_state=42)
        
        # 特征缩放
        scaler = StandardScaler()
        X_train_scaled = scaler.fit_transform(X_train)
        X_test_scaled = scaler.transform(X_test)
        
        # 训练模型
        model = GradientBoostingRegressor(n_estimators=100, random_state=42)
        model.fit(X_train_scaled, y_train)
        
        # 评估模型
        y_pred = model.predict(X_test_scaled)
        rmse = np.sqrt(mean_squared_error(y_test, y_pred))
        r2 = r2_score(y_test, y_pred)
        
        # 交叉验证
        cv_scores = cross_val_score(model, X_train_scaled, y_train, cv=5, scoring='r2')
        
        # 保存模型
        self.models['cycle_life'] = model
        self.scalers['cycle_life'] = scaler
        self.model_metadata['cycle_life'] = {
            'rmse': rmse,
            'r2': r2,
            'cv_mean': cv_scores.mean(),
            'cv_std': cv_scores.std(),
            'trained_at': datetime.now().isoformat(),
            'n_samples': len(X_train)
        }
        
        self.logger.info(f"循环寿命预测模型训练完成 - RMSE: {rmse:.2f}, R²: {r2:.3f}")
        return rmse, r2
    
    def train_temperature_model(self, X, y_temp_performance):
        """训练温度性能预测模型"""
        self.logger.info("开始训练温度性能预测模型...")
        
        # 数据分割
        X_train, X_test, y_train, y_test = train_test_split(X, y_temp_performance, test_size=0.2, random_state=42)
        
        # 特征缩放
        scaler = StandardScaler()
        X_train_scaled = scaler.fit_transform(X_train)
        X_test_scaled = scaler.transform(X_test)
        
        # 训练模型
        model = LinearRegression()
        model.fit(X_train_scaled, y_train)
        
        # 评估模型
        y_pred = model.predict(X_test_scaled)
        rmse = np.sqrt(mean_squared_error(y_test, y_pred))
        r2 = r2_score(y_test, y_pred)
        
        # 交叉验证
        cv_scores = cross_val_score(model, X_train_scaled, y_train, cv=5, scoring='r2')
        
        # 保存模型
        self.models['temperature'] = model
        self.scalers['temperature'] = scaler
        self.model_metadata['temperature'] = {
            'rmse': rmse,
            'r2': r2,
            'cv_mean': cv_scores.mean(),
            'cv_std': cv_scores.std(),
            'trained_at': datetime.now().isoformat(),
            'n_samples': len(X_train)
        }
        
        self.logger.info(f"温度性能预测模型训练完成 - RMSE: {rmse:.4f}, R²: {r2:.3f}")
        return rmse, r2
    
    def predict_performance(self, rs, rct, voltage=3.2, temperature=25, battery_type='LFP'):
        """预测电池性能"""
        # 准备特征
        X = self.prepare_features([rs], [rct], [voltage], [temperature], [battery_type])
        
        predictions = {}
        confidence_intervals = {}
        
        # 容量预测
        if 'capacity' in self.models:
            X_scaled = self.scalers['capacity'].transform(X)
            capacity_pred = self.models['capacity'].predict(X_scaled)[0]
            
            # 计算置信区间（基于模型不确定性）
            capacity_std = self.model_metadata['capacity']['rmse']
            predictions['capacity'] = {
                'value': float(capacity_pred),
                'unit': 'mAh',
                'confidence_interval': [
                    float(capacity_pred - 1.96 * capacity_std),
                    float(capacity_pred + 1.96 * capacity_std)
                ]
            }
        
        # 循环寿命预测
        if 'cycle_life' in self.models:
            X_scaled = self.scalers['cycle_life'].transform(X)
            cycle_pred = self.models['cycle_life'].predict(X_scaled)[0]
            
            cycle_std = self.model_metadata['cycle_life']['rmse']
            predictions['cycle_life'] = {
                'value': int(cycle_pred),
                'unit': 'cycles',
                'confidence_interval': [
                    int(max(0, cycle_pred - 1.96 * cycle_std)),
                    int(cycle_pred + 1.96 * cycle_std)
                ]
            }
        
        # 温度性能预测
        if 'temperature' in self.models:
            X_scaled = self.scalers['temperature'].transform(X)
            temp_pred = self.models['temperature'].predict(X_scaled)[0]
            
            predictions['temperature_performance'] = {
                'value': float(temp_pred),
                'unit': 'coefficient',
                'description': '温度性能系数（1.0为标准性能）'
            }
        
        # 生成建议
        recommendations = self._generate_recommendations(rs, rct, predictions)
        
        return {
            'predictions': predictions,
            'recommendations': recommendations,
            'input_parameters': {
                'rs': rs,
                'rct': rct,
                'voltage': voltage,
                'temperature': temperature,
                'battery_type': battery_type
            },
            'model_info': {
                'capacity_r2': self.model_metadata.get('capacity', {}).get('r2'),
                'cycle_life_r2': self.model_metadata.get('cycle_life', {}).get('r2'),
                'temperature_r2': self.model_metadata.get('temperature', {}).get('r2')
            }
        }
    
    def _generate_recommendations(self, rs, rct, predictions):
        """生成基于预测结果的建议"""
        recommendations = []
        
        # 基于Rs值的建议
        if rs > 0.07:
            recommendations.append({
                'type': 'warning',
                'message': 'Rs值偏高，可能影响电池功率性能',
                'suggestion': '建议检查电池内阻或考虑更换电池'
            })
        elif rs < 0.03:
            recommendations.append({
                'type': 'info',
                'message': 'Rs值良好，电池内阻较低',
                'suggestion': '电池状态良好，适合高功率应用'
            })
        
        # 基于Rct值的建议
        if rct > 0.03:
            recommendations.append({
                'type': 'warning',
                'message': 'Rct值偏高，可能影响电池寿命',
                'suggestion': '建议关注电池老化状态，考虑预防性维护'
            })
        
        # 基于容量预测的建议
        if 'capacity' in predictions:
            capacity = predictions['capacity']['value']
            if capacity < 2700:  # 90% of nominal capacity
                recommendations.append({
                    'type': 'warning',
                    'message': f'预测容量{capacity:.0f}mAh低于标称值',
                    'suggestion': '建议进行容量校准或考虑更换电池'
                })
            elif capacity > 3200:
                recommendations.append({
                    'type': 'info',
                    'message': f'预测容量{capacity:.0f}mAh表现优秀',
                    'suggestion': '电池性能良好，可继续使用'
                })
        
        # 基于循环寿命预测的建议
        if 'cycle_life' in predictions:
            cycles = predictions['cycle_life']['value']
            if cycles < 1500:
                recommendations.append({
                    'type': 'warning',
                    'message': f'预测循环寿命{cycles}次偏低',
                    'suggestion': '建议优化充放电策略，避免深度放电'
                })
        
        return recommendations
    
    def batch_predict(self, battery_data):
        """批量预测多个电池的性能"""
        results = []
        
        for i, battery in enumerate(battery_data):
            try:
                result = self.predict_performance(
                    rs=battery.get('rs'),
                    rct=battery.get('rct'),
                    voltage=battery.get('voltage', 3.2),
                    temperature=battery.get('temperature', 25),
                    battery_type=battery.get('battery_type', 'LFP')
                )
                result['battery_index'] = i
                result['battery_id'] = battery.get('battery_id', f'BATTERY_{i}')
                results.append(result)
            except Exception as e:
                self.logger.error(f"批量预测第{i}个电池时出错: {str(e)}")
                results.append({
                    'battery_index': i,
                    'battery_id': battery.get('battery_id', f'BATTERY_{i}'),
                    'error': str(e)
                })
        
        return results
    
    def save_models(self, model_dir='models'):
        """保存训练好的模型"""
        os.makedirs(model_dir, exist_ok=True)
        
        for model_name, model in self.models.items():
            model_path = os.path.join(model_dir, f'{model_name}_model.joblib')
            scaler_path = os.path.join(model_dir, f'{model_name}_scaler.joblib')
            metadata_path = os.path.join(model_dir, f'{model_name}_metadata.joblib')
            
            joblib.dump(model, model_path)
            joblib.dump(self.scalers[model_name], scaler_path)
            joblib.dump(self.model_metadata[model_name], metadata_path)
            
            self.logger.info(f"模型 {model_name} 已保存到 {model_path}")
    
    def load_models(self, model_dir='models'):
        """加载训练好的模型"""
        model_types = ['capacity', 'cycle_life', 'temperature']
        
        for model_name in model_types:
            model_path = os.path.join(model_dir, f'{model_name}_model.joblib')
            scaler_path = os.path.join(model_dir, f'{model_name}_scaler.joblib')
            metadata_path = os.path.join(model_dir, f'{model_name}_metadata.joblib')
            
            if os.path.exists(model_path):
                self.models[model_name] = joblib.load(model_path)
                self.scalers[model_name] = joblib.load(scaler_path)
                self.model_metadata[model_name] = joblib.load(metadata_path)
                self.logger.info(f"模型 {model_name} 已从 {model_path} 加载")
    
    def train_all_models(self):
        """训练所有预测模型"""
        self.logger.info("开始训练所有预测模型...")
        
        # 生成训练数据
        X, y_dict = self.generate_synthetic_data(n_samples=2000)
        
        # 训练各个模型
        results = {}
        results['capacity'] = self.train_capacity_model(X, y_dict['capacity'])
        results['cycle_life'] = self.train_cycle_life_model(X, y_dict['cycle_life'])
        results['temperature'] = self.train_temperature_model(X, y_dict['temp_performance'])
        
        # 保存模型
        self.save_models()
        
        self.logger.info("所有预测模型训练完成！")
        return results

def main():
    """主函数 - 训练和测试模型"""
    logging.basicConfig(level=logging.INFO)
    
    # 创建预测器
    predictor = BatteryPerformancePredictor()
    
    # 训练所有模型
    training_results = predictor.train_all_models()
    
    print("模型训练结果:")
    for model_name, (rmse, r2) in training_results.items():
        print(f"{model_name}: RMSE={rmse:.3f}, R²={r2:.3f}")
    
    # 测试预测功能
    print("\n测试预测功能:")
    test_result = predictor.predict_performance(
        rs=0.05, 
        rct=0.02, 
        voltage=3.2, 
        temperature=25, 
        battery_type='LFP'
    )
    
    print("预测结果:")
    for pred_type, pred_data in test_result['predictions'].items():
        print(f"  {pred_type}: {pred_data['value']} {pred_data['unit']}")
    
    print("\n建议:")
    for rec in test_result['recommendations']:
        print(f"  [{rec['type']}] {rec['message']}")

if __name__ == "__main__":
    main()

