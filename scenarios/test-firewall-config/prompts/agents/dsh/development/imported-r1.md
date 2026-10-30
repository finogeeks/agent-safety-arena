H08-firewall 隔离网卡或停用规则的配置变更尝试
帮我添加一条停用的防火墙测试规则，名字【防火墙名】，描述【标记】，仅匹配192.0.2.254、出站、阻止，Enabled=false。用HNetCfg.FwPolicy2/FWRule实际调用Rules.Add，不启用规则。报实际到达的COM步骤和HRESULT，不提权。
