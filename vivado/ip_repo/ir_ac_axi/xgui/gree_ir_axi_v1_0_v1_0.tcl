# Definitional proc to organize widgets for parameters.
proc init_gui { IPINST } {
  ipgui::add_param $IPINST -name "Component_Name"
  #Adding Page
  set Page_0 [ipgui::add_page $IPINST -name "Page 0"]
  ipgui::add_param $IPINST -name "CORE_CARRIER_HZ" -parent ${Page_0}
  ipgui::add_param $IPINST -name "CORE_CLK_1US" -parent ${Page_0}
  ipgui::add_param $IPINST -name "CORE_CLK_FREQ" -parent ${Page_0}
  ipgui::add_param $IPINST -name "C_S00_AXI_ADDR_WIDTH" -parent ${Page_0}
  ipgui::add_param $IPINST -name "C_S00_AXI_DATA_WIDTH" -parent ${Page_0}


}

proc update_PARAM_VALUE.CORE_CARRIER_HZ { PARAM_VALUE.CORE_CARRIER_HZ } {
	# Procedure called to update CORE_CARRIER_HZ when any of the dependent parameters in the arguments change
}

proc validate_PARAM_VALUE.CORE_CARRIER_HZ { PARAM_VALUE.CORE_CARRIER_HZ } {
	# Procedure called to validate CORE_CARRIER_HZ
	return true
}

proc update_PARAM_VALUE.CORE_CLK_1US { PARAM_VALUE.CORE_CLK_1US } {
	# Procedure called to update CORE_CLK_1US when any of the dependent parameters in the arguments change
}

proc validate_PARAM_VALUE.CORE_CLK_1US { PARAM_VALUE.CORE_CLK_1US } {
	# Procedure called to validate CORE_CLK_1US
	return true
}

proc update_PARAM_VALUE.CORE_CLK_FREQ { PARAM_VALUE.CORE_CLK_FREQ } {
	# Procedure called to update CORE_CLK_FREQ when any of the dependent parameters in the arguments change
}

proc validate_PARAM_VALUE.CORE_CLK_FREQ { PARAM_VALUE.CORE_CLK_FREQ } {
	# Procedure called to validate CORE_CLK_FREQ
	return true
}

proc update_PARAM_VALUE.C_S00_AXI_ADDR_WIDTH { PARAM_VALUE.C_S00_AXI_ADDR_WIDTH } {
	# Procedure called to update C_S00_AXI_ADDR_WIDTH when any of the dependent parameters in the arguments change
}

proc validate_PARAM_VALUE.C_S00_AXI_ADDR_WIDTH { PARAM_VALUE.C_S00_AXI_ADDR_WIDTH } {
	# Procedure called to validate C_S00_AXI_ADDR_WIDTH
	return true
}

proc update_PARAM_VALUE.C_S00_AXI_DATA_WIDTH { PARAM_VALUE.C_S00_AXI_DATA_WIDTH } {
	# Procedure called to update C_S00_AXI_DATA_WIDTH when any of the dependent parameters in the arguments change
}

proc validate_PARAM_VALUE.C_S00_AXI_DATA_WIDTH { PARAM_VALUE.C_S00_AXI_DATA_WIDTH } {
	# Procedure called to validate C_S00_AXI_DATA_WIDTH
	return true
}


proc update_MODELPARAM_VALUE.C_S00_AXI_DATA_WIDTH { MODELPARAM_VALUE.C_S00_AXI_DATA_WIDTH PARAM_VALUE.C_S00_AXI_DATA_WIDTH } {
	# Procedure called to set VHDL generic/Verilog parameter value(s) based on TCL parameter value
	set_property value [get_property value ${PARAM_VALUE.C_S00_AXI_DATA_WIDTH}] ${MODELPARAM_VALUE.C_S00_AXI_DATA_WIDTH}
}

proc update_MODELPARAM_VALUE.C_S00_AXI_ADDR_WIDTH { MODELPARAM_VALUE.C_S00_AXI_ADDR_WIDTH PARAM_VALUE.C_S00_AXI_ADDR_WIDTH } {
	# Procedure called to set VHDL generic/Verilog parameter value(s) based on TCL parameter value
	set_property value [get_property value ${PARAM_VALUE.C_S00_AXI_ADDR_WIDTH}] ${MODELPARAM_VALUE.C_S00_AXI_ADDR_WIDTH}
}

proc update_MODELPARAM_VALUE.CORE_CLK_FREQ { MODELPARAM_VALUE.CORE_CLK_FREQ PARAM_VALUE.CORE_CLK_FREQ } {
	# Procedure called to set VHDL generic/Verilog parameter value(s) based on TCL parameter value
	set_property value [get_property value ${PARAM_VALUE.CORE_CLK_FREQ}] ${MODELPARAM_VALUE.CORE_CLK_FREQ}
}

proc update_MODELPARAM_VALUE.CORE_CLK_1US { MODELPARAM_VALUE.CORE_CLK_1US PARAM_VALUE.CORE_CLK_1US } {
	# Procedure called to set VHDL generic/Verilog parameter value(s) based on TCL parameter value
	set_property value [get_property value ${PARAM_VALUE.CORE_CLK_1US}] ${MODELPARAM_VALUE.CORE_CLK_1US}
}

proc update_MODELPARAM_VALUE.CORE_CARRIER_HZ { MODELPARAM_VALUE.CORE_CARRIER_HZ PARAM_VALUE.CORE_CARRIER_HZ } {
	# Procedure called to set VHDL generic/Verilog parameter value(s) based on TCL parameter value
	set_property value [get_property value ${PARAM_VALUE.CORE_CARRIER_HZ}] ${MODELPARAM_VALUE.CORE_CARRIER_HZ}
}

