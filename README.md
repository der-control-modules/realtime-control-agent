# Real-time control Agent

![Eclipse VOLTTRON 10.0.5rc0](https://img.shields.io/badge/Eclipse%20VOLTTRON-10.0.5rc0-red.svg)
![Python 3.10](https://img.shields.io/badge/python-3.10-blue.svg)
![Python 3.11](https://img.shields.io/badge/python-3.11-blue.svg)
[![pypi version](https://img.shields.io/pypi/v/volttron-interoperability.svg)](https://pypi.org/project/volttron-interoperability/)

Main branch tests:&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; [![Main Branch Passing?](https://github.com/eclipse-volttron/volttron-interoperability/actions/workflows/run-tests.yml/badge.svg?branch=main)](https://github.com/eclipse-volttron/volttron-interoperability/actions/workflows/run-tests.yml)

Develop branch tests:&nbsp;&nbsp; [![Develop Branch Passing?](https://github.com/eclipse-volttron/volttron-interoperability/actions/workflows/run-tests.yml/badge.svg?branch=develop)](https://github.com/eclipse-volttron/volttron-interoperability/actions/workflows/run-tests.yml)


## Requirements

* python >= 3.10
* volttron >= 10.0 

## Documentation
# Real-Time Control Agent

The Real-Time (RT) Control Agent provides a framework for actuating one or more control algorithms
on an energy storage system. The RTControl framework involves the use of three abstract class types:
EnergyStorageSystem, ControlMode, and UseCase.

For each class there are several built-in subclasses, but user defined classes may also be configured and used.		
    
### EnergyStorageSystem

ESS classes abstract an energy storage system into a standard interface for use by control modes.
The base class allows configuration of points on which state of charge and power
can be monitored and (in the case of power) commanded. 
Currently two built-in ESS classes are shown in [](#storage-systems)

Table: Energy Storage Systems Implemented in the Real-Time Control Agent {#storage-systems}

| Storage System    | Description                                                                                                                                                                                                                                                                                                          |
|-------------------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| FakeESS           | Intended only for testing, commands sent to the FakeESS update in memory representations of the state of charge and power.                                                                                                                                                                                           |
| SebBESS           | This class is designed to communicate with a simple battery system which has a single control point in Watts. Other storage systems with a similar interface may be configured using the same class, or it may be used as a model for writing a custom class to command a system with a different control structure. |

### UseCase

UseCases are information services intended to collect data necessary to actualize some goal with the storage system.
The UseCase ingests data from elsewhere in the VOLTTRON ecosystem, performs any necessary model calculations or
transformations, and makes it available to control modes through properties. Eight built-in Use Cases are available,
as shown in [](#use-cases) (It should be noted that some modelled values are provided only as stubs.
These may be implemented by users who subclass these with their own model.)

Table: Use Cases Implemented in the Real-Time Control Agent {#use-cases}

| Use Case               | Description  | Inputs                                        |
|------------------------|--|-----------------------------------------------------------|
| Energy Arbitrage       | Energy arbitrage refers to the operation of energy storage that discharges when the electricity prices are high and charges when the prices are low. Since this type of energy storage operation reduces the net system load during peak hours and increases the load during off-peak hours, it is also often referred to as load leveling or load shifting. Energy arbitrage can be performed in both a vertically integrated system and in wholesale electricity markets. The economic reward is the price or cost differential between charging and discharging electrical energy minus the cost of losses during the full charging/discharging cycle. | &#x2022;&nbsp;actual_price<br/>&#x2022;&nbsp;forecast_price&nbsp;(stub)  |
| Frequency Response     | The ESS is configured to independently respond to excursions from nominal frequency by altering its power output or input. The parameters by which the control will be actuated are set using vertices or gradients in a Frequency-Watt curve. | &#x2022;&nbsp;metered_frequency                                         |
| Generation Following   | Generation is fully or partially countered by using the ESS to absorb energy (charging) when metered generation rises beyond a configured threshold. This may be used to prevent export to the grid or as a mechanism for charging the ESS when local generation is high. | &#x2022;&nbsp;forecast_power&nbsp;(stub)<br/> &#x2022;&nbsp;realtime_power                  |
| Load Following         | Load is fully or partially countered by discharging the ESS when metered load rises above some threshold. | &#x2022; forecast_power (stub)<br>&#x2022;&nbsp;realtime_power                   |
| Peak Limiting          | Metered load, beyond some configured threshold, is fully countered by discharing the ESS until load drops below this threshold again. This can be used as a mechanism to avoid capacity charges. | &#x2022;&nbsp;realtime_power                                            |
| Regulation             | The electric power system must maintain a near-real-time balance between generation and load. Balancing generation and load instantaneously and continuously is difficult because loads and generation are constantly fluctuating. Frequency regulation, also known as automatic frequency restoration reserve (aFRR) in continental Europe, are required to continuously balance generation and load under normal operating conditions. Traditionally, the majority of frequency regulation capability has been provided by specially equipped generators. As technologies evolve, new types of flexibility resources emerge, such as ESSs. | &#x2022;&nbsp;agc_signal<br/>&#x2022;&nbsp;price&nbsp;(stub)<br/>&#x2022;&nbsp;performance_score&nbsp;(stub)  |
| Variability Mitigation | A power smoothing algorithm reduces power fluctuations from renewable energy sources or volatile loads. It manages energy storage systems to store excess power during high generation or low demand, and release stored power during low generation or high demand. It employs real-time monitoring and control systems to adjust power in response to changing conditions. The algorithm enhances stability and reliability of renewable energy integration and optimizes energy storage utilization. Variability (a.k.a. ramp-rate, volatility, or intermittency) is defined as an instantaneous change in a load or source power, e.g., rapid changes in solar output power due to an intermittent cloud cover. | &#x2022;&nbsp;forecast_power&nbsp;(stub)<br/>&#x2022;&nbsp;metered_power |

### Mode

Control Modes contain the implementation of an algorithm for actuating the storage system.
These may, optionally, ingest data from UseCases. They control the storage hardware through
the interface of EnergyStorageSystem classes. Built-in control modes are described in [](#control-modes)

Table: Control Modes Implemented in the Real-Time Control Agent {#control-modes}

| Control Mode                    | Description                                                                                                                                                                                                                                                                                                    |
|---------------------------------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Active Power Limit              | Implements the MESA Active Power Limiting Mode, which disallows power commands outside of specified values.  This is used along with other control modes to constrain their output commands.                                                                                                                   |
| Active Power Response           | Implements the MESA Active Power Response Modes. This mode may be configured to provide Generation Following, Load Following, or Peak Limiting, depending on the Use Case with which it is paired.                                                                                                             |
| Active Power Smoothing          | Implements the MESA Active Power Smoothing Mode. This actuates the storage using a moving average filter applied to the measured output of a variable resource (e.g., the production meter on a photovoltaic array).                                                                                           |
| AGC                             | Implements the MESA AGC Mode. This follows an AGC command signal.                                                                                                                                                                                                                                              |
| Adaptive Moving Average Control | Similar to the Active Power Smoothing mode, but using an algorithm which self-optimizes the window of the moving average filter by using a longer window (more aggressive smoothing) when variability is high and a shorter window (which will utiilize less of the storage resource)when variability is low.  |
| Charge/Discharge Storage        | Implements the MESA Charge/Discharge Storage Mode. The battery is actuated using an ingested schedule or a pre-configured value.                                                                                                                                                                               |
| Frequency-Watt                  | Implements the MESA Frequency-Watt Mode. This utilizes a configured curve to adjust power in response to a measured frequency signal, with the goal of supporting the nominal grid frequency.                                                                                                                  | 
| PID                             | Uses a PID loop to attempt to maintain power targets in response to changes in load or generation.                                                                                                                                                                                                             |
| Rule Based                      | The rule based control is organized around developing rules to modify the battery set point from the day-ahead planning in real time.          

More detailed documentation can be found on
[ReadTheDocs](https://eclipse-volttron.readthedocs.io/en/latest/external-docs/volttron-interoperability/index.html). The RST source
of the documentation for this agent is located in the "docs" directory of this repository.

## Real-time Control Configuration

This configuration defines control logic for a simulated Battery Energy Storage System (ESS) using VOLTTRON.

---

## 🔋 ESS Settings (`ess`)

```json
{
  "ess": {
    "class_name": "FakeESS",
    "power_capacity_kw": 100,
    "energy_capacity_kwh": 125,
    "bess_topic": "devices/PNNL/BESS",
    "soc_point": "SoC",
    "power_reading_point": "",
    "actuator_vip": "",
    "power_command_point": ""
  },
  "modes": [
    {
      "name": "ActivePowerResponseName",
      "class_name": "ActivePowerResponse",
      "activation_threshold": 10.0,
      "output_ratio": 1.0,
      "ramp_params": {}
    }
  ],
  "use_cases": [
    {
      "class_name": "PeakLimiting",
      "realtime_power_topic": "devices/SomeLoad/RealPower"
    }
  ],
  "resolution": 5.0,
  "start_time": null
}
'''json

## Installation

Before installing, VOLTTRON should be installed and running.  Its virtual environment should be active.
Information on how to install of the VOLTTRON platform can be found
[here](https://github.com/eclipse-volttron/volttron-core).

#### Install and start the IEEE 1547.1 Interoperability Agent:

```shell
vctl install realtime-control-agent --vip-identity agent.rt --tag rt --start
```

#### View the status of the installed agent

```shell
vctl status
```

## Development

Please see the following for contributing guidelines [contributing](https://github.com/eclipse-volttron/volttron-core/blob/develop/CONTRIBUTING.md).

Please see the following helpful guide about [developing modular VOLTTRON agents](https://github.com/eclipse-volttron/volttron-core/blob/develop/DEVELOPING_ON_MODULAR.md)

                                                                                                                                                                |

