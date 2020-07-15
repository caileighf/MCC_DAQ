slave = load('SLAVE_DAQ/1594659887.508433.txt')
t_start_slave = 1594659887.508433;
master = load('MASTER_DAQ/1594659887.877457.txt')
t_start_master = 1594659887.877457;
figure;
time_vector_m = 0:1/19200:19199/19200;
time_vector_s = 0:1/19200:(length(slave)-1)/19200;
hold on
plot(time_vector_m,master(:,1),'r.');
plot(time_vector_s+t_start_slave-t_start_master,slave(:,1),'b.');
