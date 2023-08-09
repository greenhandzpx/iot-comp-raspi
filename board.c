#include <stdio.h>
#include <linux/i2c-dev.h>
#include <wiringPi.h>
#include <wiringSerial.h>
#include <wiringPiI2C.h>
 
#define REG_INTR_STATUS_1   0x00
#define REG_INTR_STATUS_2   0x01
#define REG_INTR_ENABLE_1   0x02
#define REG_INTR_ENABLE_2   0x03
#define REG_FIFO_WR_PTR     0x04
#define REG_OVF_COUNTER     0x05
#define REG_FIFO_RD_PTR     0x06
#define REG_FIFO_DATA       0x07
#define REG_FIFO_CONFIG     0x08
#define REG_MODE_CONFIG     0x09
#define REG_SPO2_CONFIG     0x0A
#define REG_LED1_PA         0x0C
#define REG_LED2_PA         0x0D
#define REG_PILOT_PA        0x10
#define REG_MULTI_LED_CTRL1 0x11
#define REG_MULTI_LED_CTRL2 0x12
#define REG_TEMP_INTR       0x1F
#define REG_TEMP_FRAC       0x20
#define REG_TEMP_CONFIG     0x21
#define REG_PROX_INT_THRESH 0x30
#define REG_REV_ID          0xFE
#define REG_PART_ID         0xFF
 
int num = 0;

 
void FunMax30102Init(void)
{
    //具体寄存器描述可查看MAX30102数据手册
    wiringPiI2CWriteReg8(num, REG_MODE_CONFIG  , 0x40);//复位　
    wiringPiI2CWriteReg8(num, REG_MODE_CONFIG  , 0x40);//复位<br>
    wiringPiI2CWriteReg8(num, REG_INTR_ENABLE_1, 0xC0);//中断1使能 A_FULL_EN、ALC_OVF_EN、PROX_INT_EN
    wiringPiI2CWriteReg8(num, REG_INTR_ENABLE_2, 0x00);//中断2使能 DIE_TEMP_RDY_EN
    wiringPiI2CWriteReg8(num, REG_FIFO_WR_PTR  , 0x00);//FIFO写指针
    wiringPiI2CWriteReg8(num, REG_OVF_COUNTER  , 0x00);//FIFO计数器
    wiringPiI2CWriteReg8(num, REG_FIFO_RD_PTR  , 0x00);//FIFO读指针
    wiringPiI2CWriteReg8(num, REG_FIFO_CONFIG  , 0xFF);//FIFO配置
    wiringPiI2CWriteReg8(num, REG_MODE_CONFIG  , 0x03);//设置为SPO2血氧检测模式
    wiringPiI2CWriteReg8(num, REG_SPO2_CONFIG  , 0x27);//SPO2配置
    wiringPiI2CWriteReg8(num, REG_LED1_PA      , 0x24);//LED1
    wiringPiI2CWriteReg8(num, REG_LED2_PA      , 0x24);//LED2
    wiringPiI2CWriteReg8(num, REG_PILOT_PA     , 0x7F);//
 
}
 
void FunMAX30102ReadFifo(unsigned int *PunRed, unsigned int *PunIr)
{
    //在SPO2模式下，FIFO每个样本中会包括三个字节数据，且前三个字节为 RED，后三个字节为 IR，以此类推，因此在对数据进行读取时每回需要读取6个字节，前3个字节为RED，后三个字节为IR<br>
    unsigned int Temp0 = 0;
    unsigned int Temp1 = 0;
     
    wiringPiI2CReadReg8(num, REG_INTR_STATUS_1);
    wiringPiI2CReadReg8(num, REG_INTR_STATUS_2);
     
    Temp0 = wiringPiI2CReadReg8(num, REG_FIFO_DATA);
    Temp0 <<= 16;
    *PunRed += Temp0;
    Temp0 = wiringPiI2CReadReg8(num, REG_FIFO_DATA);
    Temp0 <<= 8;
    *PunRed += Temp0;
    Temp0 = wiringPiI2CReadReg8(num, REG_FIFO_DATA);
    *PunRed += Temp0;
 
    Temp1 = wiringPiI2CReadReg8(num, REG_FIFO_DATA);
    Temp1 <<= 16;
    *PunIr += Temp1;
    Temp1 = wiringPiI2CReadReg8(num, REG_FIFO_DATA);
    Temp1 <<= 8;
    *PunIr += Temp1;
    Temp1 = wiringPiI2CReadReg8(num, REG_FIFO_DATA);
    *PunIr += Temp1;
 
    *PunRed &= 0x3FFFF;
    *PunIr  &= 0x3FFFF;
}
 
 
int main()
{
    int fd = 0;
    int Temp = 0;
    int FifoData = 0;
    unsigned int PunRed = 0;
    unsigned int PunIr  = 0;
 
    wiringPiSetup();
     
    num = wiringPiI2CSetup(0x57);//gpio i2cdetect
    if (num == -1)
    {
        printf("I2C Error\r\n");
        exit(-1):
    }
    else
    {
        printf("num = %d\r\n", num);
    }
 
    FunMax30102Init();
     
    fd = serialOpen("/dev/ttyS0",115200);
    pinMode(26,OUTPUT);
    pinMode(27,OUTPUT);
    pinMode(7, INPUT);
 
    digitalWrite(26,HIGH);
    digitalWrite(27,HIGH);
     
    while(1)
    {
        //if (digitalRead(7) == 1)
        {
            FunMAX30102ReadFifo(&PunRed, &PunIr);
            //FifoData = wiringPiI2CReadReg8(num, 0x07);
            printf("%d , %d\r\n",PunRed, PunIr);
        }       
    }
    return 0;
}