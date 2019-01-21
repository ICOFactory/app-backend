--
-- Some optimizations to the DB schema to track ERC20 tokens
--


CREATE TABLE block_data
(
    block_data_id bigint(20) unsigned PRIMARY KEY AUTO_INCREMENT,
    block_number bigint(20) unsigned,
    block_hash CHAR(66),
    block_timestamp DATETIME NOT NULL,
    gas_used int unsigned,
    gas_limit int unsigned,
    block_size int unsigned,
    tx_count int unsigned
);

CREATE UNIQUE INDEX block_data_block_hash_uindex ON block_data (block_hash);
CREATE UNIQUE INDEX block_data_block_number_uindex ON block_data (block_number DESC);

ALTER TABLE external_transaction_ledger DROP block_number;
ALTER TABLE external_transaction_ledger DROP block_timestamp;
ALTER TABLE external_transaction_ledger ADD block_data_id bigint(20) unsigned NULL;
ALTER TABLE external_transaction_ledger CHANGE external_erc20_contract_id contract_id bigint(20) unsigned;
ALTER TABLE external_transaction_ledger
  MODIFY COLUMN block_data_id bigint(20) unsigned AFTER contract_id;

ALTER TABLE external_erc20_contracts CHANGE id external_contract_id bigint(20) unsigned NOT NULL auto_increment;
ALTER TABLE external_erc20_contracts MODIFY token_name varchar(255);
ALTER TABLE external_erc20_contracts MODIFY token_symbol varchar(255);
ALTER TABLE external_erc20_contracts CHANGE block_number block_data_id bigint(20) unsigned;
ALTER TABLE external_erc20_contracts ALTER COLUMN decimals SET DEFAULT '18';
ALTER TABLE external_erc20_contracts DROP block_timestamp;

ALTER TABLE external_tokens ADD block_data_id bigint(20) unsigned NULL;
ALTER TABLE external_tokens ADD amount bigint(20) unsigned NULL;
ALTER TABLE external_tokens CHANGE external_crc_contract_id external_contract_id bigint(20) unsigned;
ALTER TABLE external_tokens DROP block_timestamp;
ALTER TABLE external_tokens DROP block_number;