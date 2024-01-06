module default {
  # NOTE: int64 is technically wrong but edgedb has no uint64
  
  function is_unique_array(arr: array<str>) -> bool
    using (array_agg(distinct array_unpack(arr)) = arr);
  function is_nonempty_str_array(arr: array<str>) -> bool
    using (select(all(len(arr) > 0)));
  # TODO: this does not work

  type User {
    required eid: int64 {
      constraint exclusive;
    }
    # required name: str;
    #
    # backlink config
    # backlink rules
  }

  type Guild {
    required eid: int64 {
      constraint exclusive;
    }
    required name: str;
  }

  type Config {
    required disabled: bool {
      default := false;
    }
    # permanent: bool = false;
  }

  type UserConfig extending Config {
    required single link Owner: User {
      constraint exclusive;
    };
    required reacts: array<str> {
      constraint expression on (is_nonempty_str_array(__subject__));
      default := <array<str>>[];
      # 1 unicode emoji or 1 discord emoji <a?:\w+:\d+>
    };
    required opens: array<str> {
      constraint expression on (is_unique_array(__subject__));
      constraint expression on (is_nonempty_str_array(__subject__));
      default := <array<str>>[];
    };
    

  }
  type GuildConfig extending Config {
    required single link Owner: Guild {
      constraint exclusive;
    };
    roles: array<int64> {
      default := <array<int64<>>[];
    };

    required timer: TimingMethod {
      default := TimingMethod.Never;
    } # cron, ale, ala
    schedule: Schedule;
    # NOTE: schedule is required if timer = TimingMethod.Cron
  }

  scalar type TimingMethod extending enum<Always, Never, Moon, Cron>;

  type Schedule {
    required timezone: str;  # ex: CST; UTC; UTC+6
    required length: str;  # ex: 2d; 4h; 30m; 4h30m
    required cron: str;  # ex: 
  }

  type Rule {
      # TODO: global rule
      required single link Owner: User | Guild;
      guild_id: int64;
      category_id: int64;
      channel_id: int64;
      # thread_id: int64;  # NOTE: waste of time?
      exception: bool;
    }
}
