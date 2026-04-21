import React, { useState } from 'react';
import {
  Modal,
  Form,
  Select,
  Checkbox,
  Button,
  Space,
  Typography,
  Row,
  Col,
  message,
  Divider,
  Alert
} from 'antd';
import {
  DownloadOutlined,
  FileExcelOutlined,
  FileTextOutlined,
  InfoCircleOutlined
} from '@ant-design/icons';
import { analysisAPI } from '../services/api';

const { Option } = Select;
const { Text } = Typography;

interface DataExportModalProps {
  visible: boolean;
  onCancel: () => void;
  selectedRowKeys: React.Key[];
  exportType?: 'test_results' | 'impedance_details';
  title?: string;
}

const DataExportModal: React.FC<DataExportModalProps> = ({
  visible,
  onCancel,
  selectedRowKeys,
  exportType = 'test_results',
  title = '数据导出'
}) => {
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);
  const [selectedFields, setSelectedFields] = useState<string[]>([]);

  // 可导出字段配置
  const fieldOptions = {
    test_results: [
      { label: 'ID', value: 'ID' },
      { label: '测试ID', value: '测试ID' },
      { label: '设备ID', value: '设备ID' },
      { label: '批次ID', value: '批次ID' },
      { label: '通道', value: '通道' },
      { label: '测试时间', value: '测试时间' },
      { label: '电压(V)', value: '电压(V)' },
      { label: 'Rs(mΩ)', value: 'Rs(mΩ)' },
      { label: 'Rct(mΩ)', value: 'Rct(mΩ)' },
      { label: '温度(°C)', value: '温度(°C)' },
      { label: '测试结果', value: '测试结果' },
      { label: '错误代码', value: '错误代码' },
      { label: '电芯类型', value: '电芯类型' },
      { label: '创建时间', value: '创建时间' }
    ],
    impedance_details: [
      { label: '测试结果ID', value: '测试结果ID' },
      { label: '测试ID', value: '测试ID' },
      { label: '设备ID', value: '设备ID' },
      { label: '通道', value: '通道' },
      { label: '频率(Hz)', value: '频率(Hz)' },
      { label: '实部阻抗(mΩ)', value: '实部阻抗(mΩ)' },
      { label: '虚部阻抗(mΩ)', value: '虚部阻抗(mΩ)' },
      { label: '阻抗模值(mΩ)', value: '阻抗模值(mΩ)' },
      { label: '相位角(°)', value: '相位角(°)' },
      { label: '测试时间', value: '测试时间' }
    ]
  };

  const currentFields = fieldOptions[exportType] || fieldOptions.test_results;

  // 处理导出
  const handleExport = async () => {
    try {
      const values = await form.validateFields();
      setLoading(true);

      const exportData = {
        test_result_ids: selectedRowKeys.map(key => Number(key)),
        format: values.format,
        fields: selectedFields.length > 0 ? selectedFields : undefined
      };

      let response;
      if (exportType === 'impedance_details') {
        response = await fetch('/api/web/export/impedance-details', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${localStorage.getItem('token')}`
          },
          body: JSON.stringify(exportData)
        });
      } else {
        response = await fetch('/api/web/export/test-results', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${localStorage.getItem('token')}`
          },
          body: JSON.stringify(exportData)
        });
      }

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.error || '导出失败');
      }

      // 处理文件下载
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      
      // 从响应头获取文件名，或使用默认文件名
      const contentDisposition = response.headers.get('Content-Disposition');
      let filename = `export_${Date.now()}.${values.format}`;
      if (contentDisposition) {
        const filenameMatch = contentDisposition.match(/filename="(.+)"/);
        if (filenameMatch) {
          filename = filenameMatch[1];
        }
      }
      
      link.download = filename;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);

      message.success('数据导出成功！');
      onCancel();

    } catch (error: any) {
      console.error('导出失败:', error);
      message.error('导出失败: ' + (error.message || '未知错误'));
    } finally {
      setLoading(false);
    }
  };

  // 全选/取消全选字段
  const handleSelectAllFields = (checked: boolean) => {
    if (checked) {
      setSelectedFields(currentFields.map(field => field.value));
    } else {
      setSelectedFields([]);
    }
  };

  // 重置表单
  const handleReset = () => {
    form.resetFields();
    setSelectedFields([]);
  };

  return (
    <Modal
      title={
        <Space>
          <DownloadOutlined />
          {title}
        </Space>
      }
      open={visible}
      onCancel={onCancel}
      width={600}
      footer={[
        <Button key="reset" onClick={handleReset}>
          重置
        </Button>,
        <Button key="cancel" onClick={onCancel}>
          取消
        </Button>,
        <Button
          key="export"
          type="primary"
          icon={<DownloadOutlined />}
          loading={loading}
          onClick={handleExport}
          disabled={selectedRowKeys.length === 0}
        >
          导出数据
        </Button>
      ]}
    >
      <Form
        form={form}
        layout="vertical"
        initialValues={{
          format: 'csv',
          fields: []
        }}
      >
        {/* 导出信息 */}
        <Alert
          message={`已选择 ${selectedRowKeys.length} 条记录进行导出`}
          type="info"
          showIcon
          style={{ marginBottom: '16px' }}
        />

        {/* 导出格式 */}
        <Form.Item
          name="format"
          label="导出格式"
          rules={[{ required: true, message: '请选择导出格式' }]}
        >
          <Select placeholder="请选择导出格式">
            <Option value="csv">
              <Space>
                <FileTextOutlined />
                CSV格式 (.csv)
              </Space>
            </Option>
            <Option value="excel">
              <Space>
                <FileExcelOutlined />
                Excel格式 (.xlsx)
              </Space>
            </Option>
          </Select>
        </Form.Item>

        <Divider />

        {/* 字段选择 */}
        <Form.Item label="导出字段">
          <div style={{ marginBottom: '8px' }}>
            <Space>
              <Checkbox
                checked={selectedFields.length === currentFields.length}
                indeterminate={selectedFields.length > 0 && selectedFields.length < currentFields.length}
                onChange={(e) => handleSelectAllFields(e.target.checked)}
              >
                全选
              </Checkbox>
              <Text type="secondary">
                ({selectedFields.length}/{currentFields.length} 已选择)
              </Text>
            </Space>
          </div>
          
          <Checkbox.Group
            value={selectedFields}
            onChange={setSelectedFields}
            style={{ width: '100%' }}
          >
            <Row gutter={[8, 8]}>
              {currentFields.map(field => (
                <Col span={12} key={field.value}>
                  <Checkbox value={field.value}>
                    {field.label}
                  </Checkbox>
                </Col>
              ))}
            </Row>
          </Checkbox.Group>
        </Form.Item>

        {/* 提示信息 */}
        <Alert
          message="导出说明"
          description={
            <div>
              <div>• 如果不选择任何字段，将导出所有可用字段</div>
              <div>• CSV格式兼容性更好，Excel格式支持更丰富的样式</div>
              <div>• 大量数据导出可能需要较长时间，请耐心等待</div>
            </div>
          }
          type="info"
          showIcon
          icon={<InfoCircleOutlined />}
          style={{ marginTop: '16px' }}
        />
      </Form>
    </Modal>
  );
};

export default DataExportModal;
