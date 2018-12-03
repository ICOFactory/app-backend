create table charting
(
  chart_data_id            bigint auto_increment
    primary key,
  moving_average_gas_price double                              null,
  node_id                  smallint(6)                         null,
  node_gas_price           bigint unsigned                     null,
  block_number             bigint unsigned                     null,
  transaction_count        int                                 null,
  block_size               int                                 null,
  gas_limit                int                                 null,
  gas_used                 int                                 null,
  node_peers               int                                 null,
  timestamp                timestamp default CURRENT_TIMESTAMP not null
);

create index charting_chart_data_id_node_id_index
  on charting (chart_data_id, node_id);