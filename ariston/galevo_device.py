"""Galevo device class for Ariston module."""
from __future__ import annotations
import asyncio

import logging
from datetime import date
from typing import Any, Optional

from .ariston_api import AristonAPI
from .const import (
    ConsumptionProperties,
    Currency,
    CustomDeviceFeatures,
    DeviceFeatures,
    DeviceProperties,
    GasEnergyUnit,
    GasType,
    PlantMode,
    PropertyType,
    ThermostatProperties,
    ZoneAttribute,
    ZoneMode,
)
from .device import AristonDevice

_LOGGER = logging.getLogger(__name__)


class AristonGalevoDevice(AristonDevice):
    """Class representing a physical device, it's state and properties."""

    def __init__(
        self,
        api: AristonAPI,
        attributes: dict[str, Any],
        is_metric: bool = True,
        language_tag: str = "en-US",
    ) -> None:
        super().__init__(api, attributes)
        self.umsys = "si" if is_metric else "us"
        self.language_tag = language_tag
        self.consumptions_settings: dict[str, Any] = dict()
        self.energy_account: dict[str, Any] = dict()

    @property
    def consumption_type(self) -> str:
        """String to get consumption type"""
        return f"Ch{'%2CDhw' if self.custom_features.get(CustomDeviceFeatures.HAS_DHW) else ''}"

    def _update_state(self) -> None:
        """Set custom features"""
        if self.custom_features.get(CustomDeviceFeatures.HAS_OUTSIDE_TEMP) is None:
            temp = self._get_item_by_id(
                DeviceProperties.OUTSIDE_TEMP, PropertyType.VALUE
            )
            max_temp = self._get_item_by_id(
                DeviceProperties.OUTSIDE_TEMP, PropertyType.MAX
            )
            self.custom_features[CustomDeviceFeatures.HAS_OUTSIDE_TEMP] = (
                temp != max_temp
            )

        if self.custom_features.get(DeviceProperties.DHW_STORAGE_TEMPERATURE) is None:
            storage_temp = self._get_item_by_id(
                DeviceProperties.DHW_STORAGE_TEMPERATURE, PropertyType.VALUE
            )
            self.custom_features[DeviceProperties.DHW_STORAGE_TEMPERATURE] = (
                storage_temp is not None
            )

    def update_state(self) -> None:
        """Update the device states from the cloud"""
        if len(self.features) == 0:
            self.get_features()

        self.data = self.api.get_properties(
            self.gw,
            self.features,
            self.language_tag,
            self.umsys,
        )
        self._update_state()

    async def async_update_state(self) -> None:
        """Async update the device states from the cloud"""
        if len(self.features) == 0:
            await self.async_get_features()

        self.data = await self.api.async_get_properties(
            self.gw,
            self.features,
            self.language_tag,
            self.umsys,
        )
        self._update_state()

    def _get_features(self) -> None:
        """Set custom features"""
        self.custom_features[CustomDeviceFeatures.HAS_DHW] = self.features.get(
            DeviceFeatures.HAS_BOILER
        )

    def get_features(self) -> None:
        """Get device features wrapper"""
        super().get_features()
        self._get_features()

    async def async_get_features(self) -> None:
        """Async get device features wrapper"""
        await super().async_get_features()
        self._get_features()

    def get_zones(self) -> list[dict[str, Any]]:
        """Get device zones wrapper"""
        return self.features.get(DeviceFeatures.ZONES, list())

    def get_zone_numbers(self) -> list[int]:
        """Get zone number for device"""
        return [zone.get(ZoneAttribute.NUM, 0) for zone in self.get_zones()]

    def get_water_heater_current_temperature(self) -> Optional[float]:
        """Get water heater current temperature"""
        if self.custom_features.get(DeviceProperties.DHW_STORAGE_TEMPERATURE):
            return self._get_item_by_id(
                DeviceProperties.DHW_STORAGE_TEMPERATURE, PropertyType.VALUE
            )
        return self._get_item_by_id(DeviceProperties.DHW_TEMP, PropertyType.VALUE)

    def get_water_heater_minimum_temperature(self) -> float:
        """Get water heater minimum temperature"""
        return self._get_item_by_id(DeviceProperties.DHW_TEMP, PropertyType.MIN)

    def get_water_heater_maximum_temperature(self) -> Optional[float]:
        """Get water heater maximum temperature"""
        return self._get_item_by_id(DeviceProperties.DHW_TEMP, PropertyType.MAX)

    def get_water_heater_target_temperature(self) -> Optional[float]:
        """Get water heater target temperature"""
        return self._get_item_by_id(DeviceProperties.DHW_TEMP, PropertyType.VALUE)

    def get_water_heater_temperature_decimals(self) -> int:
        """Get water heater temperature decimals"""
        return self._get_item_by_id(DeviceProperties.DHW_TEMP, PropertyType.DECIMALS)

    def get_water_heater_temperature_unit(self) -> str:
        """Get water heater temperature unit"""
        return self._get_item_by_id(DeviceProperties.DHW_TEMP, PropertyType.UNIT)

    def get_water_heater_temperature_step(self) -> int:
        """Get water heater temperature step"""
        return self._get_item_by_id(DeviceProperties.DHW_TEMP, PropertyType.STEP)

    def get_water_heater_mode_operation_texts(self) -> list[str]:
        """Get water heater operation mode texts"""
        return self._get_item_by_id(DeviceProperties.DHW_MODE, PropertyType.OPT_TEXTS)

    def get_water_heater_mode_options(self) -> list[int]:
        """Get water heater operation options"""
        return self._get_item_by_id(DeviceProperties.DHW_MODE, PropertyType.OPTIONS)

    def get_water_heater_mode_value(self) -> Optional[int]:
        """Get water heater mode value"""
        return self._get_item_by_id(DeviceProperties.DHW_MODE, PropertyType.VALUE)

    def get_zone_heat_request_value(self, zone_number: int) -> str:
        """Get zone heat request value"""
        return self._get_item_by_id(
            ThermostatProperties.ZONE_HEAT_REQUEST, PropertyType.VALUE, zone_number
        )

    def get_zone_economy_temp_value(self, zone_number: int) -> str:
        """Get zone economy temperature value"""
        return self._get_item_by_id(
            ThermostatProperties.ZONE_ECONOMY_TEMP, PropertyType.VALUE, zone_number
        )

    def is_plant_in_heat_mode(self) -> bool:
        """Is the plant in a heat mode"""
        return self.get_plant_mode() in [
            PlantMode.WINTER,
            PlantMode.HEATING_ONLY,
        ]

    def is_plant_in_cool_mode(self) -> bool:
        """Is the plant in a cool mode"""
        return self.get_plant_mode() in [
            PlantMode.COOLING,
            PlantMode.COOLING_ONLY,
        ]

    def is_zone_in_manual_mode(self, zone: int) -> bool:
        """Is zone in manual mode"""
        return self.get_zone_mode(zone) in [
            ZoneMode.MANUAL,
            ZoneMode.MANUAL_NIGHT,
        ]

    def is_zone_in_time_program_mode(self, zone: int) -> bool:
        """Is zone in time program mode"""
        return self.get_zone_mode(zone) in [
            ZoneMode.TIME_PROGRAM,
        ]

    def is_zone_mode_options_contains_manual(self, zone: int) -> bool:
        """Is zone mode options contains manual mode"""
        return (ZoneMode.MANUAL or ZoneMode.MANUAL_NIGHT) in self.get_zone_mode_options(
            zone
        )

    def is_zone_mode_options_contains_time_program(self, zone: int) -> bool:
        """Is zone mode options contains time program mode"""
        return ZoneMode.TIME_PROGRAM in self.get_zone_mode_options(zone)

    def is_zone_mode_options_contains_off(self, zone: int) -> bool:
        """Is zone mode options contains off mode"""
        return ZoneMode.OFF in self.get_zone_mode_options(zone)

    def is_plant_mode_options_contains_off(self) -> bool:
        """Is plant mode options contains off mode"""
        return PlantMode.OFF in self.get_plant_mode_options()

    def is_plant_mode_options_contains_cooling(self) -> bool:
        """Is plant mode options contains cooling mode"""
        return (
            PlantMode.COOLING or PlantMode.COOLING_ONLY
        ) in self.get_plant_mode_options()

    @staticmethod
    def get_zone_number(zone_number: int) -> str:
        """Get zone number"""
        return f"{zone_number}"

    def get_holiday_expires_on(self) -> str:
        """Get holiday expires on"""
        return self._get_item_by_id(DeviceProperties.HOLIDAY, PropertyType.EXPIRES_ON)

    def get_automatic_thermoregulation(self) -> str:
        """Get automatic thermoregulation"""
        return self._get_item_by_id(
            DeviceProperties.AUTOMATIC_THERMOREGULATION, PropertyType.VALUE
        )

    def get_heating_circuit_pressure_value(self) -> str:
        """Get heating circuit pressure value"""
        return self._get_item_by_id(
            DeviceProperties.HEATING_CIRCUIT_PRESSURE, PropertyType.VALUE
        )

    def get_heating_circuit_pressure_unit(self) -> str:
        """Get heating circuit pressure unit"""
        return self._get_item_by_id(
            DeviceProperties.HEATING_CIRCUIT_PRESSURE, PropertyType.UNIT
        )

    def get_ch_flow_setpoint_temp_value(self) -> str:
        """Get central heating flow setpoint temperature value"""
        return self._get_item_by_id(
            DeviceProperties.CH_FLOW_SETPOINT_TEMP, PropertyType.VALUE
        )

    def get_ch_flow_temp_value(self) -> str:
        """Get central heating flow temperature value"""
        return self._get_item_by_id(DeviceProperties.CH_FLOW_TEMP, PropertyType.VALUE)

    def get_outside_temp_value(self) -> str:
        """Get outside temperature value"""
        return self._get_item_by_id(DeviceProperties.OUTSIDE_TEMP, PropertyType.VALUE)

    def get_outside_temp_unit(self) -> str:
        """Get outside temperature unit"""
        return self._get_item_by_id(DeviceProperties.OUTSIDE_TEMP, PropertyType.UNIT)

    def get_ch_flow_setpoint_temp_unit(self) -> str:
        """Get central heating flow setpoint temperature unit"""
        return self._get_item_by_id(
            DeviceProperties.CH_FLOW_SETPOINT_TEMP, PropertyType.UNIT
        )

    def get_ch_flow_temp_unit(self) -> str:
        """Get central heating flow temperature unit"""
        return self._get_item_by_id(DeviceProperties.CH_FLOW_TEMP, PropertyType.UNIT)

    def get_is_flame_on_value(self) -> bool:
        """Get is flame on value"""
        return self._get_item_by_id(DeviceProperties.IS_FLAME_ON, PropertyType.VALUE)

    def get_holiday_mode_value(self) -> bool:
        """Get holiday mode on value"""
        return self._get_item_by_id(DeviceProperties.HOLIDAY, PropertyType.VALUE)

    def get_zone_mode(self, zone: int) -> ZoneMode:
        """Get zone mode on value"""
        zone_mode = self._get_item_by_id(
            ThermostatProperties.ZONE_MODE, PropertyType.VALUE, zone
        )

        if zone_mode is None:
            return ZoneMode.UNDEFINED

        return ZoneMode(
            self._get_item_by_id(
                ThermostatProperties.ZONE_MODE, PropertyType.VALUE, zone
            )
        )

    def get_zone_mode_options(self, zone: int) -> list[int]:
        """Get zone mode on options"""
        return self._get_item_by_id(
            ThermostatProperties.ZONE_MODE, PropertyType.OPTIONS, zone
        )

    def get_plant_mode(self) -> PlantMode:
        """Get plant mode on value"""
        plant_mode = self._get_item_by_id(
            DeviceProperties.PLANT_MODE, PropertyType.VALUE
        )

        if plant_mode is None:
            return PlantMode.UNDEFINED

        return PlantMode(plant_mode)

    def get_plant_mode_options(self) -> list[int]:
        """Get plant mode on options"""
        return self._get_item_by_id(DeviceProperties.PLANT_MODE, PropertyType.OPTIONS)

    def get_plant_mode_opt_texts(self) -> list[str]:
        """Get plant mode on option texts"""
        return self._get_item_by_id(DeviceProperties.PLANT_MODE, PropertyType.OPT_TEXTS)

    def get_plant_mode_text(self) -> str:
        """Get plant mode on option texts"""
        index = self.get_plant_mode_options().index(self.get_plant_mode())
        return self._get_item_by_id(
            DeviceProperties.PLANT_MODE, PropertyType.OPT_TEXTS
        )[index]

    def get_measured_temp_unit(self, zone: int) -> str:
        """Get zone measured temp unit"""
        return self._get_item_by_id(
            ThermostatProperties.ZONE_MEASURED_TEMP, PropertyType.UNIT, zone
        )

    def get_measured_temp_decimals(self, zone: int) -> int:
        """Get zone measured temp decimals"""
        return self._get_item_by_id(
            ThermostatProperties.ZONE_MEASURED_TEMP, PropertyType.DECIMALS, zone
        )

    def get_measured_temp_value(self, zone: int) -> int:
        """Get zone measured temp value"""
        return self._get_item_by_id(
            ThermostatProperties.ZONE_MEASURED_TEMP, PropertyType.VALUE, zone
        )

    def get_comfort_temp_min(self, zone: int) -> int:
        """Get zone comfort temp min"""
        return self._get_item_by_id(
            ThermostatProperties.ZONE_COMFORT_TEMP, PropertyType.MIN, zone
        )

    def get_comfort_temp_max(self, zone: int) -> int:
        """Get zone comfort temp max"""
        return self._get_item_by_id(
            ThermostatProperties.ZONE_COMFORT_TEMP, PropertyType.MAX, zone
        )

    def get_comfort_temp_step(self, zone: int) -> int:
        """Get zone comfort temp step"""
        return self._get_item_by_id(
            ThermostatProperties.ZONE_COMFORT_TEMP, PropertyType.STEP, zone
        )

    def get_comfort_temp_value(self, zone: int) -> int:
        """Get zone comfort temp value"""
        return self._get_item_by_id(
            ThermostatProperties.ZONE_COMFORT_TEMP, PropertyType.VALUE, zone
        )

    def get_heating_flow_offset_value(self, zone: int) -> int:
        """Get zone heating flow offset value"""
        return self._get_item_by_id(
            ThermostatProperties.HEATING_FLOW_OFFSET, PropertyType.VALUE, zone
        )

    def get_heating_flow_offset_unit(self, zone: int) -> int:
        """Get zone heating flow offset unit"""
        return self._get_item_by_id(
            ThermostatProperties.HEATING_FLOW_OFFSET, PropertyType.UNIT, zone
        )

    def get_heating_flow_offset_step(self, zone: int) -> int:
        """Get zone heating flow offset step"""
        return self._get_item_by_id(
            ThermostatProperties.HEATING_FLOW_OFFSET, PropertyType.STEP, zone
        )

    def get_heating_flow_offset_max(self, zone: int) -> int:
        """Get zone heating flow offset max"""
        return self._get_item_by_id(
            ThermostatProperties.HEATING_FLOW_OFFSET, PropertyType.MAX, zone
        )

    def get_heating_flow_offset_min(self, zone: int) -> int:
        """Get zone heating flow offset min"""
        return self._get_item_by_id(
            ThermostatProperties.HEATING_FLOW_OFFSET, PropertyType.MIN, zone
        )

    def get_heating_flow_offset_decimals(self, zone: int) -> int:
        """Get zone heating flow offset decimals"""
        return self._get_item_by_id(
            ThermostatProperties.HEATING_FLOW_OFFSET, PropertyType.DECIMALS, zone
        )

    def get_heating_flow_temp_value(self, zone: int) -> int:
        """Get zone heating flow temp value"""
        return self._get_item_by_id(
            ThermostatProperties.HEATING_FLOW_TEMP, PropertyType.VALUE, zone
        )

    def get_heating_flow_temp_unit(self, zone: int) -> int:
        """Get zone heating flow temp unit"""
        return self._get_item_by_id(
            ThermostatProperties.HEATING_FLOW_TEMP, PropertyType.UNIT, zone
        )

    def get_heating_flow_temp_step(self, zone: int) -> int:
        """Get zone heating flow temp step"""
        return self._get_item_by_id(
            ThermostatProperties.HEATING_FLOW_TEMP, PropertyType.STEP, zone
        )

    def get_heating_flow_temp_max(self, zone: int) -> int:
        """Get zone heating flow temp max"""
        return self._get_item_by_id(
            ThermostatProperties.HEATING_FLOW_TEMP, PropertyType.MAX, zone
        )

    def get_heating_flow_temp_min(self, zone: int) -> int:
        """Get zone heating flow temp min"""
        return self._get_item_by_id(
            ThermostatProperties.HEATING_FLOW_TEMP, PropertyType.MIN, zone
        )

    def get_heating_flow_temp_decimals(self, zone: int) -> int:
        """Get zone heating flow temp decimals"""
        return self._get_item_by_id(
            ThermostatProperties.HEATING_FLOW_TEMP, PropertyType.DECIMALS, zone
        )

    def _get_item_by_id(
        self, item_id: str, item_value: str, zone_number: int = 0
    ) -> Any:
        """Get item attribute from data"""
        return next(
            (
                item.get(item_value)
                for item in self.data.get("items", dict())
                if item.get("id") == item_id
                and item.get(PropertyType.ZONE) == zone_number
            ),
            None,
        )

    def get_elect_cost(self) -> Optional[float]:
        """Get electric consumption cost"""
        return self.consumptions_settings.get(ConsumptionProperties.ELEC_COST)

    def get_gas_cost(self) -> Optional[float]:
        """Get gas consumption cost"""
        return self.consumptions_settings.get(ConsumptionProperties.GAS_COST)

    def get_gas_type(self) -> Optional[str]:
        """Get gas type"""
        gas_type = self.consumptions_settings.get(ConsumptionProperties.GAS_TYPE)
        if gas_type in list(GasType):
            return GasType(gas_type).name
        return None

    @staticmethod
    def get_gas_types() -> list[Optional[str]]:
        """Get all gas types"""
        return [c.name for c in GasType]

    def set_gas_type(self, selected: str):
        """Set gas type"""
        self._set_consumptions_settings(
            ConsumptionProperties.GAS_TYPE, GasType[selected]
        )

    async def async_set_gas_type(self, selected: str):
        """Async set gas type"""
        await self._async_set_consumptions_settings(
            ConsumptionProperties.GAS_TYPE, GasType[selected]
        )

    def get_currency(self) -> Optional[str]:
        """Get gas type"""
        currency = self.consumptions_settings.get(ConsumptionProperties.CURRENCY)
        if currency in list(Currency):
            return Currency(
                self.consumptions_settings.get(ConsumptionProperties.CURRENCY)
            ).name
        return None

    @staticmethod
    def get_currencies() -> list[Optional[str]]:
        """Get all currency"""
        return [c.name for c in Currency]

    def set_currency(self, selected: str):
        """Set currency"""
        self._set_consumptions_settings(
            ConsumptionProperties.CURRENCY, Currency[selected]
        )

    async def async_set_currency(self, selected: str):
        """Async set currency"""
        await self._async_set_consumptions_settings(
            ConsumptionProperties.CURRENCY, Currency[selected]
        )

    def get_gas_energy_unit(self) -> Optional[str]:
        """Get gas energy unit"""
        gas_energy_unit = self.consumptions_settings.get(ConsumptionProperties.GAS_ENERGY_UNIT)
        if gas_energy_unit in list(GasEnergyUnit):
            return GasEnergyUnit(
                self.consumptions_settings.get(ConsumptionProperties.GAS_ENERGY_UNIT)
            ).name
        return None

    @staticmethod
    def get_gas_energy_units() -> list[Optional[str]]:
        """Get all gas energy unit"""
        return [c.name for c in GasEnergyUnit]

    def set_gas_energy_unit(self, selected: str):
        """Set gas energy unit"""
        self._set_consumptions_settings(
            ConsumptionProperties.GAS_ENERGY_UNIT, GasEnergyUnit[selected]
        )

    async def async_set_gas_energy_unit(self, selected: str):
        """Async set gas energy unit"""
        await self._async_set_consumptions_settings(
            ConsumptionProperties.GAS_ENERGY_UNIT, GasEnergyUnit[selected]
        )

    def get_gas_consumption_for_heating_last_month(self) -> Optional[int]:
        """Get gas consumption for heatig last month"""
        energy_account_last_month = self.energy_account.get("LastMonth", None)
        if not energy_account_last_month:
            return None
        return energy_account_last_month[0].get("gas", None)

    def get_electricity_consumption_for_heating_last_month(self) -> Optional[int]:
        """Get electricity consumption for heating last month"""
        energy_account_last_month = self.energy_account.get("LastMonth", None)
        if not energy_account_last_month:
            return None
        return energy_account_last_month[0].get("elect", None)

    def get_gas_consumption_for_water_last_month(self) -> Optional[int]:
        """Get gas consumption for water last month"""
        energy_account_last_month = self.energy_account.get("LastMonth", None)
        if not energy_account_last_month or len(energy_account_last_month) < 2:
            return None
        return energy_account_last_month[1].get("gas", None)

    def get_electricity_consumption_for_water_last_month(self) -> Optional[int]:
        """Get electricity consumption for water last month"""
        energy_account_last_month = self.energy_account.get("LastMonth", None)
        if not energy_account_last_month or len(energy_account_last_month) < 2:
            return None
        return energy_account_last_month[1].get("elect", None)

    def set_elect_cost(self, value: float):
        """Set electric cost"""
        self._set_consumptions_settings(ConsumptionProperties.ELEC_COST, value)

    async def async_set_elect_cost(self, value: float):
        """Async set electric cost"""
        await self._async_set_consumptions_settings(
            ConsumptionProperties.ELEC_COST, value
        )

    def set_gas_cost(self, value: float):
        """Set gas cost"""
        self._set_consumptions_settings(ConsumptionProperties.GAS_COST, value)

    async def async_set_gas_cost(self, value: float):
        """Async set gas cost"""
        await self._async_set_consumptions_settings(
            ConsumptionProperties.GAS_COST, value
        )

    def _set_consumptions_settings(self, consumption_property: str, value: float):
        """Set consumption settings"""
        new_settings = self.consumptions_settings.copy()
        new_settings[consumption_property] = value
        self.api.set_consumptions_settings(self.gw, new_settings)
        self.consumptions_settings[consumption_property] = value

    async def _async_set_consumptions_settings(
        self, consumption_property: str, value: float
    ):
        """Async set consumption settings"""
        new_settings = self.consumptions_settings.copy()
        new_settings[consumption_property] = value
        await self.api.async_set_consumptions_settings(self.gw, new_settings)
        self.consumptions_settings[consumption_property] = value

    def set_water_heater_temperature(self, temperature: float):
        """Set water heater temperature"""
        self.set_item_by_id(DeviceProperties.DHW_TEMP, temperature)

    async def async_set_water_heater_temperature(self, temperature: float):
        """Async set water heater temperature"""
        await self.async_set_item_by_id(DeviceProperties.DHW_TEMP, temperature)

    def set_water_heater_operation_mode(self, operation_mode: str):
        """Set water heater operation mode"""
        self.set_item_by_id(
            DeviceProperties.DHW_MODE,
            self._get_item_by_id(
                DeviceProperties.DHW_MODE, PropertyType.OPT_TEXTS
            ).index(operation_mode),
        )

    async def async_set_water_heater_operation_mode(self, operation_mode: str):
        """Async set water heater operation mode"""
        await self.async_set_item_by_id(
            DeviceProperties.DHW_MODE,
            self._get_item_by_id(
                DeviceProperties.DHW_MODE, PropertyType.OPT_TEXTS
            ).index(operation_mode),
        )

    def set_automatic_thermoregulation(self, auto_thermo: bool):
        """Set automatic thermoregulation"""
        self.set_item_by_id(
            DeviceProperties.AUTOMATIC_THERMOREGULATION, 1.0 if auto_thermo else 0.0
        )

    async def async_set_automatic_thermoregulation(self, auto_thermo: bool):
        """Async set automatic thermoregulation"""
        await self.async_set_item_by_id(
            DeviceProperties.AUTOMATIC_THERMOREGULATION, 1.0 if auto_thermo else 0.0
        )

    def set_plant_mode(self, plant_mode: PlantMode):
        """Set plant mode"""
        self.set_item_by_id(DeviceProperties.PLANT_MODE, plant_mode)

    async def async_set_plant_mode(self, plant_mode: PlantMode):
        """Async set plant mode"""
        await self.async_set_item_by_id(DeviceProperties.PLANT_MODE, plant_mode)

    def set_zone_mode(self, zone_mode: ZoneMode, zone: int):
        """Set zone mode"""
        self.set_item_by_id(ThermostatProperties.ZONE_MODE, zone_mode, zone)

    async def async_set_zone_mode(self, zone_mode: ZoneMode, zone: int):
        """Async set zone mode"""
        await self.async_set_item_by_id(ThermostatProperties.ZONE_MODE, zone_mode, zone)

    def set_comfort_temp(self, temp: float, zone: int):
        """Set comfort temp"""
        self.set_item_by_id(ThermostatProperties.ZONE_COMFORT_TEMP, temp, zone)

    async def async_set_comfort_temp(self, temp: float, zone: int):
        """Async set comfort temp"""
        await self.async_set_item_by_id(
            ThermostatProperties.ZONE_COMFORT_TEMP, temp, zone
        )

    def set_heating_flow_temp(self, temp: float, zone: int):
        """Set heating flow temp"""
        self.set_item_by_id(ThermostatProperties.HEATING_FLOW_TEMP, temp, zone)

    async def async_set_heating_flow_temp(self, temp: float, zone: int):
        """Async set heating flow temp"""
        await self.async_set_item_by_id(
            ThermostatProperties.HEATING_FLOW_TEMP, temp, zone
        )

    def set_heating_flow_offset(self, offset: float, zone: int):
        """Set heating flow offset"""
        self.set_item_by_id(ThermostatProperties.HEATING_FLOW_OFFSET, offset, zone)

    async def async_set_heating_flow_offset(self, offset: float, zone: int):
        """Async set heating flow offset"""
        await self.async_set_item_by_id(
            ThermostatProperties.HEATING_FLOW_OFFSET, offset, zone
        )

    def _set_item_by_id(
        self,
        item_id: str,
        value: float,
        zone_number: int = 0,
    ):
        for item in self.data.get("items", dict()):
            if item.get("id") == item_id and item.get(PropertyType.ZONE) == zone_number:
                item[PropertyType.VALUE] = value
                break

    def set_item_by_id(
        self,
        item_id: str,
        value: float,
        zone_number: int = 0,
    ):
        """Set item attribute on device"""
        current_value = self._get_item_by_id(item_id, PropertyType.VALUE, zone_number)
        self.api.set_property(
            self.gw,
            zone_number,
            self.features,
            item_id,
            value,
            current_value,
            self.umsys,
        )
        self._set_item_by_id(item_id, value, zone_number)

    async def async_set_item_by_id(
        self,
        item_id: str,
        value: float,
        zone_number: int = 0,
    ):
        """Async set item attribute on device"""
        current_value = self._get_item_by_id(item_id, PropertyType.VALUE, zone_number)
        await self.api.async_set_property(
            self.gw,
            zone_number,
            self.features,
            item_id,
            value,
            current_value,
            self.umsys,
        )
        self._set_item_by_id(item_id, value, zone_number)

    @staticmethod
    def _create_holiday_end_date(holiday_end: date):
        return (
            None if holiday_end is None else holiday_end.strftime("%Y-%m-%dT00:00:00")
        )

    def _set_holiday(self, holiday_end_date: Optional[str]):
        for item in self.data.get("items", dict()):
            if item.get("id") == DeviceProperties.HOLIDAY:
                item[PropertyType.VALUE] = False if holiday_end_date is None else True
                item[PropertyType.EXPIRES_ON] = (
                    None if holiday_end_date is None else holiday_end_date
                )
                break

    def set_holiday(self, holiday_end: date):
        """Set holiday on device"""
        holiday_end_date = self._create_holiday_end_date(holiday_end)
        self.api.set_holiday(self.gw, holiday_end_date)
        self._set_holiday(holiday_end_date)

    async def async_set_holiday(self, holiday_end: date):
        """Async set holiday on device"""
        holiday_end_date = self._create_holiday_end_date(holiday_end)
        await self.api.async_set_holiday(self.gw, holiday_end_date)
        self._set_holiday(holiday_end_date)

    def update_energy(self) -> None:
        """Update the device energy settings from the cloud"""
        super().update_energy()

        # These settings only for official clients
        self.consumptions_settings = self.api.get_consumptions_settings(self.gw)
        # Last month consumption in kwh
        self.energy_account = self.api.get_energy_account(self.gw)

    async def async_update_energy(self) -> None:
        """Async update the device energy settings from the cloud"""
        (_, self.consumptions_settings, self.energy_account) = await asyncio.gather(
            super().async_update_energy(),
            # These settings only for official clients
            self.api.async_get_consumptions_settings(self.gw),
            # Last month consumption in kwh
            self.api.async_get_energy_account(self.gw),
        )
