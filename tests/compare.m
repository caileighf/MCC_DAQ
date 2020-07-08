slave = load('1594160158.114738.txt')
t_start_slave = 1594160158.114738;
master = load('1594160157.707541.txt')
t_start_master = 1594160157.707541;
figure;
time_vector_m = 0:1/19200:19199/19200;
time_vector_s = 0:1/19200:(length(slave)-1)/19200;
hold on
plot(time_vector_m,master(:,1),'r.');
plot(time_vector_s+t_start_slave-t_start_master,slave(:,1),'b.');
