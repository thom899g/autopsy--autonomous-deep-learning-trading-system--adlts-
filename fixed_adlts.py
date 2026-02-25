#!/usr/bin/env python3
"""
AUTONOMOUS DEEP LEARNING TRADING SYSTEM (ADLTS) - FIXED VERSION
Production-ready trading system with robust configuration management,
Firebase integration, and comprehensive error handling.
"""

import os
import json
import logging
import sys
from dataclasses import dataclass, asdict
from enum import Enum
from typing import Optional, Dict, Any, List
from datetime import datetime
import traceback

# External dependencies (must be installed via pip)
try:
    import numpy as np
    import pandas as pd
    import firebase_admin
    from firebase_admin import credentials, firestore
    from google.cloud import firestore as gc_firestore
except ImportError as e:
    print(f"Missing dependency: {e}")
    print("Please install: pip install numpy pandas firebase-admin google-cloud-firestore")
    sys.exit(1)


class TradingMode(Enum):
    """Trading operation modes"""
    BACKTEST = "backtest"
    PAPER = "paper"
    LIVE = "live"
    ANALYSIS = "analysis"


@dataclass
class ModelConfig:
    """Neural network model configuration"""
    learning_rate: float = 0.001
    batch_size: int = 32
    hidden_layers: List[int] = None
    dropout_rate: float = 0.2
    activation: str = "relu"
    epochs: int = 100
    validation_split: float = 0.2
    
    def __post_init__(self):
        """Initialize default values for lists"""
        if self.hidden_layers is None:
            self.hidden_layers = [128, 64, 32]


@dataclass
class RLConfig:
    """Reinforcement Learning configuration"""
    gamma: float = 0.99
    epsilon_start: float = 1.0
    epsilon_end: float = 0.01
    epsilon_decay: float = 0.995
    memory_capacity: int = 10000
    target_update_freq: int = 100
    learning_starts: int = 1000


@dataclass
class TradingConfig:
    """Trading system configuration"""
    mode: TradingMode = TradingMode.PAPER
    initial_balance: float = 10000.0
    max_position_size: float = 0.1  # 10% of portfolio
    stop_loss_pct: float = 0.02  # 2%
    take_profit_pct: float = 0.05  # 5%
    trading_fee: float = 0.001  # 0.1%
    risk_free_rate: float = 0.02
    symbols: List[str] = None
    timeframe: str = "1h"
    
    def __post_init__(self):
        """Initialize default values and validate"""
        if self.symbols is None:
            self.symbols = ["BTC/USDT", "ETH/USDT"]
        
        # Ensure mode is TradingMode enum
        if isinstance(self.mode, str):
            self.mode = TradingMode(self.mode)


class AutonomousDeepLearningTradingSystem:
    """
    Main trading system class with fixed configuration management
    and robust error handling.
    """
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize the trading system with configuration.
        
        Args:
            config_path: Optional path to JSON configuration file
        """
        # Initialize logging first
        self._init_logging()
        
        # Initialize configurations with defaults
        self.model_config = ModelConfig()
        self.rl_config = RLConfig()
        self.trading_config = TradingConfig()
        
        # Initialize state variables
        self.firestore_client: Optional[gc_firestore.Client] = None
        self.is_initialized: bool = False
        self.start_time: Optional[datetime] = None
        
        try:
            # Load configuration if provided
            if config_path:
                self._load_config(config_path)
            
            # Initialize Firebase
            self._init_firebase()
            
            # Validate all configurations
            self._validate()
            
            # Mark as initialized
            self.is_initialized = True
            self.start_time = datetime.now()
            
            self.logger.info("ADLTS initialized successfully")
            self.logger.info(f"Trading mode: {self.trading_config.mode.value}")
            self.logger.info(f"Model learning rate: {self.model_config.learning_rate}")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize ADLTS: {e}")
            self.logger.error(traceback.format_exc())
            raise
    
    def _init_logging(self) -> None:
        """Initialize comprehensive logging system"""
        # Create logger
        self.logger = logging.getLogger('ADLTS')
        self.logger.setLevel(logging.DEBUG)
        
        # Avoid duplicate handlers
        if not self.logger.handlers:
            # Console handler
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setLevel(logging.INFO)
            
            # Formatter
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            console_handler.setFormatter(formatter)
            
            self.logger.addHandler(console_handler)
    
    def _load_config(self, config_path: str) -> None:
        """
        Load configuration from JSON file with comprehensive error handling.
        
        Args:
            config_path