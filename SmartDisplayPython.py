import spidev
import Adafruit_DHT
import paho.mqtt.client as mqtt
import time
import struct
import serial
 
spi = spidev.SpiDev() #configuration du SPI
spi.open(0, 0)
spi.max_speed_hz = 1350000
ser = serial.Serial('/dev/ttyUSB0', baudrate=9600, timeout=2) #configuration du port serial a lire
 
#fonction de lecture du capteur d'humidité et de température (dht22), avec comme variable "pin" la broche du raspberry a lire (qui doit être celle ou le capteur est
def read_dht(pin):
    humidity, temperature = Adafruit_DHT.read_retry(Adafruit_DHT.DHT22, pin)
    return humidity, temperature
 
#fonction de lecture du CAN (ADC en anglais), avec comme variable "channel" la broche du CAN a lire (donc la broche sur lequel le capteur est branché)
def read_adc(channel, vref=3.3):
    adc = spi.xfer2([1, (8 + channel) << 4, 0]) #lecture de la valeur renvoyé par le CAN (formules chatgtp)
    data = ((adc[1] & 3) << 8) + adc[2]      
    tension = data * vref / 1023.0 #calculs de conversions de la valeur renvoyé par le CAN en tension puis en décibels (les formules ont été trouvé sur la datasheet du capteur)
    decibels = tension * 50    
    return decibels
 
def read_airquality():
        data = ser.read(10)
        if len(data)==10 and data[0]==0xAA and data[1]==0xC0 and data[9]==0xAB:
            pm25 = struct.unpack('<H', data[2:4])[0]/10.0
            pm10 = struct.unpack('<H', data[4:6])[0]/10.0
            return pm25, pm10
 
def main():
    capteur_temp_humi = 4 #broche de la raspberry
    capteur_son_cannal = 0 #broche CONVERISSEUR    
    broker_adress = "raspberrypimatheo1" #adresse du serveur MQTT (si pas herbergé en local preciser adresse IP)
    #Format de nommage du topic : "salle/variable"
    mqtt_topic_humidity = "KM103/humidity"
    mqtt_topic_temperature = "KM103/temperature"
    mqtt_topic_sound_level = "KM103/decibels"
    mqtt_topic_air_quality = "KM103/air_quality"
    mqtt_topic_emergency = "KM103/emergency"
   
    #nom du client qui va se connecter sur MQQTT (au cas ou on configure des utilisateurs authorisés sur MQTT)
    client = mqtt.Client("Capteurs/KM103")
    client.connect(broker_adress)
    client.publish(mqtt_topic_emergency, "non")
 
    try:
        while True:
            humidity, temperature = read_dht(capteur_temp_humi)
            humidity = round(humidity, 1)
            temperature = round(temperature, 1)
            print(f"Humidité = {humidity}%")
            print(f"Température = {temperature}°C")
           
            sound_level = read_adc(capteur_son_cannal, vref=3.3)
            sound_level = round(sound_level, 1)
            print(f"Niveau sonore : {sound_level}dcb")
           
            pm25, pm10 = read_airquality()
            quality_level = pm25 + pm10
            quality_level = round(quality_level, 1)            
            print(f"Indice de qualitué de l'air: {quality_level}")
           
            #publier les valeurs des capteurs dans le même topic "Données des capteurs" mais dans des sous-topics différents (pour faciliter la récupération)
            client.publish(mqtt_topic_humidity, humidity)
            client.publish(mqtt_topic_temperature, temperature)
            client.publish(mqtt_topic_sound_level, sound_level)
            client.publish(mqtt_topic_air_quality, quality_level)
            message = (f"{{'Humidité': {humidity}%, 'Temperature': {temperature}°C, 'Niveau sonore': {sound_level}dcb, 'Qualité de l'air': {pm25}}}")
            print(f"Les données suivantes sont publiées sur le serveur MQTT : {message}")
 
            time.sleep(1)#temps d'attente boucle    
    except KeyboardInterrupt:
        print("Programme terminé.")
    finally:
        spi.close()
 
if __name__ == '__main__':
 
    main()
