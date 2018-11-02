CREATE TABLE `access_control_list` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `user_id` int(11) unsigned NOT NULL,
  `smart_contract_id` smallint(5) unsigned DEFAULT NULL,
  `permission` varchar(55) DEFAULT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

CREATE TABLE `commands` (
  `command_id` bigint(20) unsigned NOT NULL AUTO_INCREMENT,
  `node_id` smallint(5) unsigned NOT NULL,
  `command` text,
  `created` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `dispatch_event_id` int(20) unsigned DEFAULT NULL,
  PRIMARY KEY (`command_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

CREATE TABLE `devices` (
  `device_id` int(10) unsigned NOT NULL AUTO_INCREMENT,
  `uuid` char(36) NOT NULL,
  `owner_id` int(10) unsigned NOT NULL,
  `created` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`device_id`),
  UNIQUE KEY `uuid` (`uuid`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

CREATE TABLE `ethereum_address_pool` (
  `id` bigint(20) unsigned NOT NULL AUTO_INCREMENT,
  `ethereum_address` char(42) DEFAULT NULL,
  `assigned` datetime DEFAULT NULL,
  `created` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

CREATE TABLE `ethereum_network` (
  `id` smallint(5) unsigned NOT NULL AUTO_INCREMENT,
  `node_identifier` varchar(55) DEFAULT NULL,
  `last_event_id` bigint(20) unsigned DEFAULT NULL,
  `last_update` datetime DEFAULT NULL,
  `last_update_ip` varchar(15) DEFAULT NULL,
  `api_key` varchar(32) DEFAULT NULL,
  `status` enum('Unknown','Syncing','Synchronized','Restarting','Error') DEFAULT 'Unknown',
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

CREATE TABLE `event_log` (
  `event_id` bigint(20) unsigned NOT NULL AUTO_INCREMENT,
  `event_type_id` smallint(5) unsigned DEFAULT NULL,
  `user_id` int(10) unsigned DEFAULT NULL,
  `json_metadata` longtext,
  `created` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`event_id`),
  KEY `event_log_event_type_id_index` (`event_type_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

CREATE TABLE `credits` (
  `credit_id` bigint(20) unsigned NOT NULL AUTO_INCREMENT,
  `user_id` int unsigned NOT NULL,
  `amount` bigint(20) unsigned DEFAULT 0,
  `event_id` bigint(20) unsigned NOT NULL,
  `created` timestamp  NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY(`credit_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

CREATE TABLE `debits` (
  `debit_id` bigint(20) unsigned NOT NULL AUTO_INCREMENT,
  `user_id` int unsigned NOT NULL,
  `amount` bigint(20) unsigned DEFAULT 0,
  `event_id` bigint(20) unsigned NOT NULL,
  `created` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ,
  PRIMARY KEY(`debit_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

CREATE TABLE `event_type` (
  `event_type_id` smallint(5) unsigned NOT NULL AUTO_INCREMENT,
  `event_type` varchar(55) DEFAULT NULL,
  PRIMARY KEY (`event_type_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

CREATE TABLE `frames` (
  `frame_id` int(10) unsigned NOT NULL AUTO_INCREMENT,
  `device_id` int(10) unsigned NOT NULL,
  `created` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `viewed` datetime DEFAULT NULL,
  `metadata` text,
  PRIMARY KEY (`frame_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

CREATE TABLE `smart_contracts` (
  `id` smallint(5) unsigned NOT NULL AUTO_INCREMENT,
  `token_name` varchar(55) DEFAULT NULL,
  `tokens` bigint(20) unsigned DEFAULT NULL,
  `eth_address` bigint(20) unsigned DEFAULT NULL,
  `solidity_source` text,
  `created` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `max_priority` int unsigned DEFAULT 10,
  `token_symbol` varchar(55) DEFAULT NULL,
  `published` datetime DEFAULT NULL,
  `owner_id` int unsigned DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `token_name` (`token_name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

CREATE TABLE `tokens` (
  `serial` bigint(20) unsigned NOT NULL AUTO_INCREMENT,
  `eth_address` bigint(20) unsigned DEFAULT NULL,
  `owner_id` int(10) unsigned DEFAULT NULL,
  `smart_contract_id` smallint(5) unsigned DEFAULT NULL,
  `issued` datetime DEFAULT NULL,
  `created` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`serial`),
  KEY `tokens_smart_contract_id_index` (`smart_contract_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

CREATE TABLE `transaction_ledger` (
  `txid` bigint(20) unsigned NOT NULL AUTO_INCREMENT,
  `token_id` bigint(20) unsigned DEFAULT NULL,
  `sender_id` int(10) unsigned DEFAULT NULL,
  `receiver_id` int(10) unsigned DEFAULT NULL,
  `initiated_by` int(10) unsigned DEFAULT NULL,
  `external_address` char(42) DEFAULT NULL,
  `timestamp` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`txid`),
  KEY `transaction_ledger_token_id_index` (`token_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

CREATE TABLE `users` (
  `user_id` int(10) unsigned NOT NULL AUTO_INCREMENT,
  `email_address` varchar(55) DEFAULT NULL,
  `password` char(64) DEFAULT NULL,
  `last_logged_in` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `last_logged_in_ip` varchar(15) DEFAULT NULL,
  `created` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `created_ip` varchar(15) DEFAULT NULL,
  `session_token` char(16) DEFAULT NULL,
  `json_metadata` text,
  `full_name` varchar(255) DEFAULT NULL,
  PRIMARY KEY (`user_id`),
  UNIQUE KEY `email_address` (`email_address`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;
