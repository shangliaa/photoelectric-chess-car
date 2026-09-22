# vl53l0x.py — VL53L0X 激光测距驱动（单发模式）
# 两个模块默认地址都是 0x29，通过 XSHUT 引脚逐个复位并改地址
# 参考 ST VL53L0X API 精简实现

from machine import Pin, I2C
import time
import config

VL53L0X_DEFAULT_ADDR = 0x29

# 寄存器（部分关键）
REG_SYSRANGE_START = 0x00
REG_SYSTEM_SEQUENCE_CONFIG = 0x01
REG_SYSTEM_INTERRUPT_CONFIG = 0x0A
REG_SYSTEM_INTERRUPT_CLEAR = 0x0B
REG_RESULT_RANGE_STATUS = 0x14
REG_RESULT_PHASECAL_LIM = 0x30
REG_ALGO_PHASECAL_LIM = 0x30
REG_MSRC_CONFIG = 0x60
REG_FINAL_RATE_RTN_LIMIT = 0x44
REG_SYSRANGE_VHV_RECALIBRATE = 0x2D
REG_SYSRANGE_VHV_REPEAT_RATE = 0x31
REG_INTERNAL_TIMEOUT = 0x5B
REG_GLOBAL_CONFIG_SPAD_ENABLES = 0x4F
REG_GLOBAL_CONFIG_REF_EN_START_SELECT = 0x46
REG_DYNAMIC_SPAD_NUM_REQUESTED_REF_SPAD = 0x4E
REG_DYNAMIC_SPAD_REF_EN_START_OFFSET = 0x4F
REG_POWER_MANAGEMENT_GO1_POWER_FORCE = 0x80
REG_POWER_MANAGEMENT_VCSEL_PERIOD = 0x84
REG_POWER_MANAGEMENT_VCSEL_WDT = 0x85
REG_SLAVE_DEVICE_ADDRESS = 0x8A
REG_VHV_CONFIG_PAD_SCL_SDA__EXTSUP_HV = 0x89


class VL53L0X:
    def __init__(self, i2c: I2C, xshut_pin=None, address=VL53L0X_DEFAULT_ADDR):
        self._i2c = i2c
        self._addr = address
        self._xshut = Pin(xshut_pin, Pin.OUT) if xshut_pin is not None else None
        if self._xshut is not None:
            self._xshut.value(0)
        self._init_done = False

    def _write8(self, reg, val):
        self._i2c.writeto_mem(self._addr, reg, bytes([val]))

    def _write16(self, reg, val):
        self._i2c.writeto_mem(self._addr, reg, bytes([(val >> 8) & 0xFF, val & 0xFF]))

    def _write32(self, reg, val):
        self._i2c.writeto_mem(self._addr, reg, bytes([
            (val >> 24) & 0xFF, (val >> 16) & 0xFF,
            (val >> 8) & 0xFF, val & 0xFF]))

    def _read8(self, reg):
        return self._i2c.readfrom_mem(self._addr, reg, 1)[0]

    def _read16(self, reg):
        data = self._i2c.readfrom_mem(self._addr, reg, 2)
        return (data[0] << 8) | data[1]

    def power_on(self):
        if self._xshut is not None:
            self._xshut.value(1)
            time.sleep_ms(2)

    def power_off(self):
        if self._xshut is not None:
            self._xshut.value(0)

    def set_address(self, new_addr):
        self._write8(REG_SLAVE_DEVICE_ADDRESS, new_addr & 0x7F)
        self._addr = new_addr

    def init(self):
        self.power_on()
        time.sleep_ms(10)
        # 检查 ID
        vid = self._read16(0x00C0)
        # 简化初始化：参考 ST 标准流程
        self._write8(0x88, 0x00)
        self._write8(0x80, 0x01)
        self._write8(0xFF, 0x01)
        self._write8(0x00, 0x00)
        self._write8(0xFF, 0x00)
        self._write8(0x00, 0x01)
        self._write8(0xFF, 0x01)
        self._write8(0x80, 0x00)
        self._write8(0xFF, 0x00)
        self._write8(0x01, 0x08)
        self._write8(0xFF, 0x01)
        self._write8(0x00, 0x00)
        self._write8(0xFF, 0x00)
        self._write8(0x00, 0x00)
        # 配置信号率阈值
        self._write16(REG_FINAL_RATE_RTN_LIMIT, 0x1000)  # 0.25 MCPS
        self._write8(REG_MSRC_CONFIG, 0x00)
        # VCSEL 周期
        self._write8(REG_POWER_MANAGEMENT_VCSEL_PERIOD, 0x09)
        self._write8(REG_POWER_MANAGEMENT_VCSEL_WDT, 0x14)
        # 序列配置
        self._write8(REG_SYSTEM_SEQUENCE_CONFIG, 0x04)  # 仅测距
        # 距离模式：默认
        self._init_done = True
        time.sleep_ms(10)
        return True

    def read_range(self):
        """单发测距，返回毫米值；失败返回 -1。"""
        if not self._init_done:
            return -1
        # 启动单发
        self._write8(REG_SYSRANGE_START, 0x01)
        # 等待完成（轮询中断状态位）
        for _ in range(100):
            status = self._read8(0x13)
            if status & 0x07:
                break
            time.sleep_ms(2)
        else:
            return -1
        # 读取距离
        rng = self._read16(0x1E)
        # 清除中断
        self._write8(REG_SYSTEM_INTERRUPT_CLEAR, 0x01)
        if rng > 8190:
            return -1
        return rng


class DualRanging:
    """双 VL53L0X：左、右。开机时用 XSHUT 区分地址。"""

    def __init__(self, i2c: I2C):
        self._i2c = i2c
        self.left = VL53L0X(i2c, config.PIN_VL53L0X_L_XSHUT, VL53L0X_DEFAULT_ADDR)
        self.right = VL53L0X(i2c, config.PIN_VL53L0X_R_XSHUT, VL53L0X_DEFAULT_ADDR)
        # 先全部关电
        self.left.power_off()
        self.right.power_off()
        time.sleep_ms(5)
        # 左：上电 -> 改地址 -> 初始化
        self.left.power_on()
        time.sleep_ms(5)
        self.left.set_address(0x30)
        self.left.init()
        # 右：上电 -> 改地址 -> 初始化
        self.right.power_on()
        time.sleep_ms(5)
        self.right.set_address(0x31)
        self.right.init()

    def read(self):
        return self.left.read_range(), self.right.read_range()


# ---- 单元测试：串口打印左右测距值，用手遮挡测试 ----
if __name__ == '__main__':
    i2c = I2C(0, scl=Pin(config.PIN_I2C_SCL), sda=Pin(config.PIN_I2C_SDA), freq=config.I2C_FREQ)
    dual = DualRanging(i2c)
    print('VL53L0X 双测距测试：')
    while True:
        l, r = dual.read()
        print(f'L={l}mm  R={r}mm')
        time.sleep_ms(200)
