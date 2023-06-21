import mysql.connector
from openpyxl import Workbook
from datetime import timedelta
from openpyxl.utils.dataframe import dataframe_to_rows
import time


def main(s_date, connection):
    # вводим дата начала
    start_date = input('Введите дату в формате yyyy-mm-dd: ')
    # крайняя дата(правый предел)
    print(f'Скачиваем данные по 1 дню начниная с {start_date}')
    while start_date < '2023-06-10':
        print(f'Скачиваем данные за {start_date}')
        with connection.cursor() as cursor:
            cursor.execute(
                f"""
    SET @trcid = 40; -- Алматыэлектротранс
    
    SET @datestart = "{start_date}";
    
    -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- --
    
    SET @dateend   = DATE_ADD(@datestart, INTERVAL 1 day);
    
    SELECT * FROM (
        SELECT t.id `ID`,
            r.name `Маршрут`,
            tr.name `Терминал`,
            con.name `Кондуктор`,
            c.longPan `ПАН Карты`,
            ctn.nn `Тип Карты`,
            t.summ DIV 100 `Стоимость`,
            t.tripNo `№ Рейса`,
            DATE_FORMAT(t.passDt, '%Y%m%d') `Дата`,
            DATE_FORMAT(t.passDate, '%H:%i:%s') `Время`,
            DATE_FORMAT(t.createDt, '%Y%m%d') `Дата Обр.`,
            DATE_FORMAT(t.createDate, '%H:%i:%s') `Время Обр.`,
            IF(c.test = 1, 'Да', 'Нет') `Тестовая`,
            IF(fa.servicePrefix = 'OID', fly.flyId, '') `OID`,
            IF(fa.servicePrefix = 'OID', fid.agentTransactionId, '') `WID`,
            ctx.nn `Тип Обсл.`
        FROM pc_transactions t
                 LEFT JOIN pc_trcs trc ON trc.id = t.trcId
                 LEFT JOIN pc_cities cis ON cis.id = trc.cityId
                 LEFT JOIN pc_routes r ON r.id = t.routeId
                 LEFT JOIN pc_trms tr ON tr.id = t.trmId
                 LEFT JOIN pc_conductors con ON con.id = t.conductorId
                 JOIN pc_cards c ON c.id = t.cardId
                 LEFT JOIN pc_card_types ct ON ct.id = c.cardTypeId
                 LEFT JOIN pc_pass_transactions pt ON pt.transactionId = t.id
                 LEFT JOIN pc_transactions_qr qr ON qr.transactionId = t.id
                 LEFT JOIN pc_fly_transactions fly ON fly.transactionId = t.id
                 LEFT JOIN pc_transactions_bag bag ON bag.transactionId = t.id
                 LEFT JOIN pc_fly_agents fa ON fa.id = fly.flyAgentId
                 LEFT JOIN pc_fly_agent_ids fid ON fid.transactionId = fly.transactionId
                 LEFT JOIN pc_card_types ctf ON ctf.id = fa.cardTypeId
                 LEFT JOIN pc_transactions_kids k
        ON k.transactionId = t.id AND (ct.nativeCityId IS NULL OR ct.nativeCityId = 1)
                 JOIN pc_card_types ctn ON ctn.nn =
                                           IF(c.cardTypeId != 2,
                                              IF(pt.transactionId IS NULL,
                                                 IF(fly.transactionId IS NULL OR fly.flyAgentId < 3 OR fly.flyAgentId = 18,
                                                    IF(qr.transactionId IS NULL,
                                                       IF(bag.transactionId IS NULL, ct.nn, CONCAT(ct.nn, '.01')),
                                                       CONCAT(ct.nn, '.03')),
                                                    ctf.nn
                                                     ),
                                                 CONCAT(ct.nn, '.02')
                                                  ),
                                              IF(pt.transactionId IS NULL,
                                                 IF(k.transactionId IS NULL,
                                                    IF(qr.transactionId IS NULL, ct.nn, CONCAT(ct.nn, '.03')),
                                                    IF(k.age >= 15,
                                                       CONCAT(IF(qr.transactionId IS NULL, ct.nn, CONCAT(ct.nn, '.03')),
                                                              '.15'),
                                                       CONCAT(IF(qr.transactionId IS NULL, ct.nn, CONCAT(ct.nn, '.03')),
                                                              '.07'))
                                                     ),
                                                 IF(k.transactionId IS NULL, CONCAT(ct.nn, '.02'),
                                                    IF(k.age >= 15, CONCAT(ct.nn, '.02.15'), CONCAT(ct.nn, '.02.07'))
                                                     )
                                                  )
                                               )
                 LEFT JOIN pc_card_types_aliases a ON a.cityId = cis.id AND a.sourceCardTypeId = ctn.id
                 LEFT JOIN pc_card_types ctx ON ctx.id = IFNULL(a.targetCardTypeId, ctn.id)
        WHERE t.trcId = @trcid AND
            ctn.isHidden = 0 AND
            -- t.createDt = @datestart
            t.createDt >= @datestart AND t.createDt < @dateend
        UNION ALL
        SELECT t.preSellId `ID`,
            r.name `Маршрут`,
            tr.name `Терминал`,
            con.name `Кондуктор`,
            t.longPan `ПАН Карты`,
            ctn.nn `Тип Карты`,
            t.summ `Стоимость`,
            t.tripNo `№ Рейса`,
            DATE_FORMAT(t.passDt, '%Y%m%d') `Дата`,
            DATE_FORMAT(t.passDate, '%H:%i:%s') `Время`,
            DATE_FORMAT(t.loadDate, '%Y%m%d') `Дата Обр.`,
            DATE_FORMAT(t.loadDate, '%H:%i:%s') `Время Обр.`,
            'Нет' `Тестовая`,
            NULL,
            NULL,
            ctx.nn `Тип Обсл.`
        FROM vc_transactions t
                 LEFT JOIN pc_trcs trc ON trc.id = t.trcId
                 LEFT JOIN pc_cities cis ON cis.id = trc.cityId
                 LEFT JOIN pc_routes r ON r.id = t.routeId
                 LEFT JOIN pc_trms tr ON tr.id = t.trmId
                 LEFT JOIN pc_conductors con ON con.id = t.conductorId
                 LEFT JOIN pc_card_types ctn ON ctn.id = t.cardTypeId
                 LEFT JOIN pc_card_types_aliases a ON a.cityId = cis.id AND a.sourceCardTypeId = ctn.id
                 LEFT JOIN pc_card_types ctx ON ctx.id = IFNULL(a.targetCardTypeId, ctn.id)
        WHERE t.trcId = @trcid AND
            ctx.isHidden = 0 AND
            -- t.createDt >= @datestart AND t.createDt < @dateend
            t.createDate >= @datestart AND t.createDate < @dateend
    ) x
    ORDER BY `Дата Обр.`, `Время Обр.`
    ;""")
        # извлекаем данные
        result = cursor.fetchall()
        workbook = Workbook()
        sheet = workbook.active
        for row in dataframe_to_rows(result, index=False, header=False):
            sheet.append(row)
        # сохраняем файл
        workbook.save(f"{start_date}.xlsx")
        print(f"Результаты запроса сохранены в файл: {start_date}.xlsx")
        start_date = s_date + timedelta(days=1)
        print(f"Слудующая дата {start_date}")
        time.sleep(2)
    cursor.close()


def machina(user, password, host, port, database):
    try:
        # Устанавливаем соединение с базой данных
        connection = mysql.connector.connect(
            user=user,
            password=password,
            host=host,
            port=port,
            database=database
        )
        connection.autocommit = True
        # Проверяем, что соединение установлено успешно
        if connection.is_connected():
            print("Соединение установлено")
            print(f"Привет {user}, мы подключаемся к {database}, {host}")
            main(connection)
    except mysql.connector.Error as error:
        print("Ошибка при работе с MySQL:", error)
    finally:
        # Закрываем соединение с базой данных
        if connection and connection.is_connected():
            connection.close()
            print("Соединение с базой данных закрыто")

def config():
    print('Давайте подключимся к MySQL')
    time.sleep(1)
    user = 's.korytko'
    password = 'FXfXSqcRNpSgG2x4SdOsAeuorpkFEaqT'
    host = '172.18.1.3'
    port = 3306
    database = 'MySQL'
    machina(user, password, host, port, database)

if __name__ == '__main__':
    config()
