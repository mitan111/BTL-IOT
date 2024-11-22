// Arduino code
const int greenPin_1 = 12;
const int yellowPin_1 = 10;
const int redPin_1 = 8;
const int greenPin_2 = 6;
const int yellowPin_2 = 4;
const int redPin_2 = 2;


void setup() {
    pinMode(greenPin_1, OUTPUT);
    pinMode(yellowPin_1, OUTPUT);
    pinMode(redPin_1, OUTPUT);
    pinMode(greenPin_2, OUTPUT);
    pinMode(yellowPin_2, OUTPUT);
    pinMode(redPin_2, OUTPUT);
    Serial.begin(9600);
}

void loop() {
    if (Serial.available() > 0) {
        char command = Serial.read();
        if (command == 'G') {
            digitalWrite(greenPin_1, HIGH);
            digitalWrite(redPin_1, LOW);
        } else if (command == 'Y') {
            digitalWrite(greenPin_1, LOW);
            digitalWrite(yellowPin_1, HIGH);
        } else if (command == 'R') {
            digitalWrite(yellowPin_1, LOW);
            digitalWrite(redPin_1, HIGH);
        } else if (command == 'A') {
            digitalWrite(greenPin_2, HIGH);
            digitalWrite(redPin_2, LOW);
        } else if (command == 'B') {
            digitalWrite(greenPin_2, LOW);
            digitalWrite(yellowPin_2, HIGH);
        } else if (command == 'C') {
            digitalWrite(yellowPin_2, LOW);
            digitalWrite(redPin_2, HIGH);
        }
        
    }
}
