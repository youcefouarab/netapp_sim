-- ============================
--     CoS table definition
-- ============================

create table if not exists cos (
	id integer primary key,
  	name text not null unique,
    max_response_time real,
    min_concurrent_users real,
    min_requests_per_second real,
    min_bandwidth real,
    max_delay real,
    max_jitter real,
    max_loss_rate real,
    min_cpu integer,
    min_ram real,
    min_disk real
);

insert into cos (id, name,               min_cpu, min_ram, min_disk)
         values (1,  'best-effort',      1,       1000,    1),
                (2,  'cpu-bound',        1,       1000,    1),
                (3,  'streaming',        1,       1000,    1),
                (4,  'conversational',   1,       1000,    1),
                (5,  'interactive',      1,       1000,    1),
                (6,  'real-time',        1,       1000,    1),
                (7,  'mission-critical', 1,       1000,    1);

-- =================================
--     Requests table definition
-- =================================

create table if not exists requests (
	id text primary key,
  	cos_id integer not null,
    state integer,
    host text,
    data blob,
    result blob,
    hreq_at real,
    hres_at real,
    rres_at real,
    dres_at real,

    constraint fk_cos
    foreign key (cos_id)  
    references cos (id)  
);