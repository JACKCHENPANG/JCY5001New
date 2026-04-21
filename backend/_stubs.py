"""
Stub classes for backend functionality removed in clean version.
Only maintains import compatibility, no actual backend functionality.
"""

from PyQt5.QtCore import QObject


class CommunicationManager:
    """Stub for CommunicationManager - backend removed"""
    def __init__(self, config=None):
        print("Warning: CommunicationManager is stub - backend removed")
        self.status_callback = None
        self.config = config
        self.is_connected = False

    def set_status_callback(self, callback):
        self.status_callback = callback

    def connect(self, *args, **kwargs):
        return False

    def disconnect(self):
        pass

    def send_command(self, *args, **kwargs):
        return None

    def is_device_connected(self):
        return False

    def get_status_info(self):
        return {}

    def reconnect_with_new_port(self, new_port):
        return False

    def perform_health_check(self):
        return False


class TestEngine:
    """Stub for TestEngine - backend removed"""
    def __init__(self):
        print("Warning: TestEngine is stub - backend removed")

    def run_test(self, *args, **kwargs):
        pass

    def stop_test(self):
        pass

    def get_device_info(self):
        return {}


class DataProcessor:
    """Stub for DataProcessor - backend removed"""
    def __init__(self):
        print("Warning: DataProcessor is stub - backend removed")

    def process_data(self, *args, **kwargs):
        pass


class VoltageBasedBatteryDetectionManager(QObject):
    """Stub for VoltageBasedBatteryDetectionManager - backend removed"""
    def __init__(self, comm_manager, config_manager):
        super().__init__()
        print("Warning: VoltageBasedBatteryDetectionManager is stub - backend removed")
        self.comm_manager = comm_manager
        self.config_manager = config_manager

    def set_callbacks(self, status_callback, measurement_callback, battery_removed_callback=None):
        pass

    def start_detection(self):
        pass

    def stop_detection(self):
        pass


class HeartbeatManager(QObject):
    """Stub for HeartbeatManager - backend removed"""
    def __init__(self, config=None):
        super().__init__()
        print("Warning: HeartbeatManager is stub - backend removed")
        self.config = config

    def set_status_callback(self, callback):
        pass

    def is_sync_enabled(self):
        return False


class DataUploadManager(QObject):
    """Stub for DataUploadManager - backend removed"""
    def __init__(self, config=None, db_manager=None):
        super().__init__()
        print("Warning: DataUploadManager is stub - backend removed")
        self.config = config

    def is_sync_enabled(self):
        return False

    def set_heartbeat_manager(self, hm):
        pass

    def start_services_delayed(self, delay_seconds=5):
        pass


class LabelTemplateManager:
    """Stub for LabelTemplateManager - backend removed"""
    def __init__(self, config=None):
        print("Warning: LabelTemplateManager is stub - backend removed")

    def get_template(self, template_id):
        return None

    def get_all_templates(self):
        return []

    def save_template(self, template):
        return False

    def delete_template(self, template_id):
        return False


class TestResultManager:
    """Stub for TestResultManager - backend removed"""
    def __init__(self, db_path=None):
        print("Warning: TestResultManager is stub - backend removed")


class TestFlowManager(QObject):
    """Stub for TestFlowManager - backend removed"""
    def __init__(self, config_manager=None, comm_manager=None, device_connection_manager=None, parent=None):
        super().__init__(parent)
        print("Warning: TestFlowManager is stub - backend removed")

    def start_test(self):
        pass

    def stop_test(self):
        pass


class TestControlWidget:
    """Stub for TestControlWidget - backend removed"""
    def __init__(self, parent=None):
        print("Warning: TestControlWidget is stub - backend removed")
        self.parent = parent

    def start_test(self):
        pass

    def stop_test(self):
        pass
