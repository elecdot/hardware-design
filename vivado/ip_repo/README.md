# ip_repo

Shared Vivado IP repository for packaged reusable custom AXI IP.

## Convention

- Keep authoritative RTL source under [../../rtl/](../../rtl/).
- Package reusable custom IP into subdirectories here, for example
  `vivado/ip_repo/axi_i2c_jy901/`.
- Configure Vivado projects under [../project/](../project/) to reference this
  shared directory with `ip_repo_paths` and `update_ip_catalog`.
- Do not maintain one packaged IP copy per Vivado project unless it is a
  documented temporary experiment.

## Git Tracking

Track the packaged IP files needed to rediscover and reuse the IP, such as
`component.xml`, `xgui/`, and required HDL or data files emitted by the packager.
Do not treat Vivado-generated cache, run directories, hardware exports,
`ip_user_files`, simulation output, journals, or logs as design source.

