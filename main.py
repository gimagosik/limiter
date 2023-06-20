import mysql.connector
from openpyxl import Workbook
from datetime import datetime, timedelta
from openpyxl.utils.dataframe import dataframe_to_rows


def start_date(connection):
    # вводим дата начала
    s_date = input('Введите дату в формате yyyy-mm-dd: ')
    all_tran(s_date, connection)


def all_tran(s_date, connection):
    # крайняя дата(правый предел)
    while s_date < '2023-06-10':
        with connection.cursor() as cursor:
            cursor.execute(
                f"""
    SET @trcid = 40; -- Алматыэлектротранс
    
    SET @datestart = "{s_date}";
    
    -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- --
    
    SET @dateend   = DATE_ADD(@datestart, INTERVAL 10 day);
    
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
    LIMIT 1000000
    ;
                """)
        # извлекаем данные
        result = cursor.fetchall()
        filename = s_date
        workbook = Workbook()
        sheet = workbook.active
        last_row = sheet.max_row
        # определяем последнюю дату цикла
        last_date = sheet.cell(row=last_row, column=11).value
        for row in dataframe_to_rows(result, index=False, header=False):
            sheet.append(row)
        # сохраняем файл
        workbook.save(f"{filename}-{last_date}.xlsx")
        print(f"Результаты запроса сохранены в файл: {filename}")
        s_date = last_date + timedelta(days=1)
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
            start_date(connection)
    except mysql.connector.Error as error:
        print("Ошибка при работе с MySQL:", error)
    finally:
        # Закрываем соединение с базой данных
        if connection and connection.is_connected():
            connection.close()
            print("Соединение с базой данных закрыто")

def config():
    print('Давайте подключимся к MySQL')
    user = input("Введите имя пользователя: ")
    password = input("Пароль: ")
    host = input("Хост: ")
    port = input("Порт: ")
    database = input("Название базы данных: ")
    machina(user, password, host, port, database)

if __name__ == '__main__':
    config()
