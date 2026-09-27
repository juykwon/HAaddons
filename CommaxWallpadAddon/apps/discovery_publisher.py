"""홈어시스턴트 MQTT Discovery 메시지 발행을 담당하는 모듈"""

import json
from typing import Dict, Any, List, Tuple
from .logger import Logger


class DiscoveryPublisher:
    def __init__(self, controller):
        self.controller = controller
        self.logger: Logger = controller.logger
        self.discovery_prefix = "homeassistant"

        # availability 설정
        self.availability_topic = f"{self.controller.HA_TOPIC}/status"
        self.availability = {
            "availability": [
                {
                    "topic": self.availability_topic,
                    "payload_available": "online",
                    "payload_not_available": "offline",
                }
            ]
        }

    def _device_info(self, device_name: str, idx: int) -> Dict[str, Any]:
        """device_id 기준으로 Home Assistant Device 정보를 생성한다."""
        device_id = f"{device_name}{idx}"
        device_labels = {
            "Light": ("코맥스 조명", "COMMAX Wallpad Light"),
            "Thermo": ("코맥스 난방", "COMMAX Wallpad Thermostat"),
            "Ventilator": ("코맥스 환풍기", "COMMAX Wallpad Ventilator"),
            "LightBreaker": ("코맥스 일괄소등", "COMMAX Wallpad Light Breaker"),
            "Gas": ("코맥스 가스", "COMMAX Wallpad Gas Valve"),
            "Outlet": ("코맥스 콘센트", "COMMAX Wallpad Outlet"),
            "EV": ("코맥스 엘리베이터", "COMMAX Wallpad Elevator"),
        }
        name_prefix, model = device_labels.get(
            device_name, (f"코맥스 {device_name}", f"COMMAX Wallpad {device_name}")
        )

        return {
            "device": {
                "identifiers": [f"commax_{device_id}"],
                "name": f"{name_prefix} {idx}",
                "model": model,
                "manufacturer": "COMMAX",
            }
        }

    def _common_payload(self, device_name: str, idx: int) -> Dict[str, Any]:
        """Discovery payload에 공통으로 들어가는 device/availability 정보를 반환한다."""
        return {
            **self._device_info(device_name, idx),
            **self.availability,
        }

    async def publish_discovery_message(self):
        """홈어시스턴트 MQTT Discovery 메시지 발행"""
        try:
            if self.controller.device_list is None:
                self.logger.error("device_list가 초기화되지 않았습니다.")
                return

            for device_name, device_info in self.controller.device_list.items():
                device_type = device_info["type"]
                device_count = device_info["count"]

                # device_count가 0인 경우 건너뛰기
                if device_count == 0:
                    continue

                # 1부터 시작
                for idx in range(1, device_count + 1):
                    device_id = f"{device_name}{idx}"
                    common_payload = self._common_payload(device_name, idx)

                    # config_topic과 payload를 리스트로 관리
                    configs: List[Tuple[str, dict]] = []

                    if device_type == "switch":  # 기타 스위치
                        if device_name == "Outlet":  # 콘센트인 경우
                            # 스위치 설정
                            configs.append(
                                (
                                    f"{self.discovery_prefix}/switch/{device_id}/config",
                                    {
                                        "name": f"{device_name} {idx}",
                                        "object_id": f"commax_{device_id}",
                                        "unique_id": f"commax_{device_id}",
                                        "state_topic": self.controller.STATE_TOPIC.format(
                                            device_id, "power"
                                        ),
                                        "command_topic": f"{self.controller.HA_TOPIC}/{device_id}/power/command",
                                        "payload_on": "ON",
                                        "payload_off": "OFF",
                                        "device_class": "outlet",
                                        **common_payload,
                                    },
                                )
                            )
                            # 자동전력차단모드 스위치 설정
                            configs.append(
                                (
                                    f"{self.discovery_prefix}/switch/{device_id}_ecomode/config",
                                    {
                                        "name": f"{device_name} {idx} 자동대기전력차단",
                                        "object_id": f"commax_{device_id}_ecomode",
                                        "unique_id": f"commax_{device_id}_ecomode",
                                        "state_topic": self.controller.STATE_TOPIC.format(
                                            device_id, "ecomode"
                                        ),
                                        "command_topic": f"{self.controller.HA_TOPIC}/{device_id}/ecomode/command",
                                        "payload_on": "ON",
                                        "payload_off": "OFF",
                                        **common_payload,
                                    },
                                )
                            )
                            # 자동전력차단값 설정
                            configs.append(
                                (
                                    f"{self.discovery_prefix}/number/{device_id}_cutoff_value/config",
                                    {
                                        "name": f"{device_name} {idx} 자동대기전력차단값",
                                        "object_id": f"commax_{device_id}_cutoff_value",
                                        "unique_id": f"commax_{device_id}_cutoff_value",
                                        "state_topic": self.controller.STATE_TOPIC.format(
                                            device_id, "cutoff"
                                        ),
                                        "command_topic": f"{self.controller.HA_TOPIC}/{device_id}/setCutoff/command",
                                        "step": 1,
                                        "min": 0,
                                        "max": 500,
                                        "mode": "box",
                                        "unit_of_measurement": "W",
                                        **common_payload,
                                    },
                                )
                            )
                            # 전력 센서 설정
                            configs.append(
                                (
                                    f"{self.discovery_prefix}/sensor/{device_id}_watt/config",
                                    {
                                        "name": f"{device_name} {idx} 소비전력",
                                        "object_id": f"commax_{device_id}_watt",
                                        "unique_id": f"commax_{device_id}_watt",
                                        "state_topic": self.controller.STATE_TOPIC.format(
                                            device_id, "watt"
                                        ),
                                        "unit_of_measurement": "W",
                                        "device_class": "power",
                                        "state_class": "measurement",
                                        **common_payload,
                                    },
                                )
                            )
                        else:  # 일반 스위치인 경우
                            configs.append(
                                (
                                    f"{self.discovery_prefix}/switch/{device_id}/config",
                                    {
                                        "name": f"{device_name} {idx}",
                                        "object_id": f"commax_{device_id}",
                                        "unique_id": f"commax_{device_id}",
                                        "state_topic": self.controller.STATE_TOPIC.format(
                                            device_id, "power"
                                        ),
                                        "command_topic": f"{self.controller.HA_TOPIC}/{device_id}/power/command",
                                        "payload_on": "ON",
                                        "payload_off": "OFF",
                                        **common_payload,
                                    },
                                )
                            )
                    elif device_type == "light":  # 조명
                        configs.append(
                            (
                                f"{self.discovery_prefix}/light/{device_id}/config",
                                {
                                    "name": f"조명 {idx}",
                                    "object_id": f"commax_{device_id}",
                                    "unique_id": f"commax_{device_id}",
                                    "state_topic": self.controller.STATE_TOPIC.format(
                                        device_id, "power"
                                    ),
                                    "command_topic": f"{self.controller.HA_TOPIC}/{device_id}/power/command",
                                    "payload_on": "ON",
                                    "payload_off": "OFF",
                                    **common_payload,
                                },
                            )
                        )
                    elif device_type == "fan":  # 환기장치
                        configs.append(
                            (
                                f"{self.discovery_prefix}/fan/{device_id}/config",
                                {
                                    "name": f"환기장치 {idx}",
                                    "object_id": f"commax_{device_id}",
                                    "unique_id": f"commax_{device_id}",
                                    "state_topic": self.controller.STATE_TOPIC.format(
                                        device_id, "power"
                                    ),
                                    "command_topic": f"{self.controller.HA_TOPIC}/{device_id}/power/command",
                                    "speed_state_topic": self.controller.STATE_TOPIC.format(
                                        device_id, "speed"
                                    ),
                                    "speed_command_topic": f"{self.controller.HA_TOPIC}/{device_id}/speed/command",
                                    "speeds": ["low", "medium", "high"],
                                    "payload_on": "ON",
                                    "payload_off": "OFF",
                                    **common_payload,
                                },
                            )
                        )
                    elif device_type == "climate":  # 온도조절기
                        configs.append(
                            (
                                f"{self.discovery_prefix}/climate/{device_id}/config",
                                {
                                    "name": f"난방 {idx}",
                                    "object_id": f"commax_{device_id}",
                                    "unique_id": f"commax_{device_id}",
                                    "current_temperature_topic": self.controller.STATE_TOPIC.format(
                                        device_id, "curTemp"
                                    ),
                                    "temperature_command_topic": f"{self.controller.HA_TOPIC}/{device_id}/setTemp/command",
                                    "temperature_state_topic": self.controller.STATE_TOPIC.format(
                                        device_id, "setTemp"
                                    ),
                                    "mode_command_topic": f"{self.controller.HA_TOPIC}/{device_id}/power/command",
                                    "mode_state_topic": self.controller.STATE_TOPIC.format(
                                        device_id, "power"
                                    ),
                                    "action_topic": self.controller.STATE_TOPIC.format(
                                        device_id, "action"
                                    ),
                                    "action_template": "{% if value == 'off' %}off{% elif value == 'idle' %}idle{% elif value == 'heating' %}heating{% endif %}",
                                    "modes": ["off", "heat"],
                                    "temperature_unit": "C",
                                    "min_temp": int(
                                        self.controller.config["climate_settings"].get(
                                            "min_temp", 5
                                        )
                                    ),
                                    "max_temp": int(
                                        self.controller.config["climate_settings"].get(
                                            "max_temp", 40
                                        )
                                    ),
                                    "temp_step": 1,
                                    **common_payload,
                                },
                            )
                        )
                    elif device_type == "button":  # 버튼형 기기 (가스밸브잠금, 엘리베이터 호출)
                        configs.append(
                            (
                                f"{self.discovery_prefix}/button/{device_id}/config",
                                {
                                    "name": f"{device_name} {idx}",
                                    "object_id": f"commax_{device_id}",
                                    "unique_id": f"commax_{device_id}",
                                    "command_topic": f"{self.controller.HA_TOPIC}/{device_id}/button/command",
                                    "payload_press": "PRESS",
                                    **common_payload,
                                },
                            )
                        )
                    if device_name == "EV":  # 엘리베이터 층수 센서
                        configs.append(
                            (
                                f"{self.discovery_prefix}/sensor/{device_id}_floor/config",
                                {
                                    "name": f"엘리베이터 {idx} 층",
                                    "object_id": f"commax_{device_id}_floor",
                                    "unique_id": f"commax_{device_id}_floor",
                                    "state_topic": self.controller.STATE_TOPIC.format(
                                        device_id, "floor"
                                    ),
                                    **common_payload,
                                },
                            )
                        )
                    elif device_name == "Gas":  # 가스밸브 상태 센서
                        configs.append(
                            (
                                f"{self.discovery_prefix}/binary_sensor/{device_id}/config",
                                {
                                    "name": f"가스밸브 {idx}",
                                    "object_id": f"commax_{device_id}_valve",
                                    "unique_id": f"commax_{device_id}_valve",
                                    "state_topic": self.controller.STATE_TOPIC.format(
                                        device_id, "power"
                                    ),
                                    "payload_on": "ON",
                                    "payload_off": "OFF",
                                    **common_payload,
                                },
                            )
                        )

                    # 모든 config 발행
                    for config_topic, payload in configs:
                        self.controller.publish_mqtt(
                            config_topic, json.dumps(payload), retain=True
                        )

            self.logger.info("MQTT Discovery 설정 완료")

        except Exception as e:
            self.logger.error(f"MQTT Discovery 설정 중 오류 발생: {str(e)}")
